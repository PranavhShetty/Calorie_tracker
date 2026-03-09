import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { API_URL } from '../App';
import { useNavigate } from 'react-router-dom';

// ── Audio Transcription Hook (MediaRecorder → Groq Whisper) ──────
function useAudioTranscription(apiUrl) {
  const [isRecording, setIsRecording]     = useState(false);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [activeField, setActiveField]     = useState(null);

  const mediaRecorderRef = useRef(null);
  const chunksRef        = useRef([]);
  const onTextRef        = useRef(null);
  const fieldRef         = useRef(null);

  const start = async (field, onText) => {
    if (!navigator.mediaDevices) {
      alert('Microphone not supported in this browser.');
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      chunksRef.current  = [];
      onTextRef.current  = onText;
      fieldRef.current   = field;

      const mr = new MediaRecorder(stream);
      mediaRecorderRef.current = mr;

      mr.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };

      mr.onstop = async () => {
        stream.getTracks().forEach(t => t.stop());
        const blob = new Blob(chunksRef.current, { type: 'audio/webm' });
        setIsTranscribing(true);
        try {
          const formData = new FormData();
          formData.append('audio', blob, 'audio.webm');
          const res  = await fetch(`${apiUrl}/api/transcribe`, { method: 'POST', body: formData });
          const data = await res.json();
          if (data.transcript) {
            onTextRef.current(prev => prev ? prev + ' ' + data.transcript : data.transcript);
          } else {
            alert('Transcription failed: ' + (data.error || 'Unknown error'));
          }
        } catch (e) {
          console.error('Transcription error:', e);
          alert('Failed to send audio for transcription.');
        } finally {
          setIsTranscribing(false);
          setActiveField(null);
        }
      };

      mr.start();
      setIsRecording(true);
      setActiveField(field);
    } catch (e) {
      if (e.name === 'NotAllowedError') {
        alert('Microphone access denied. Please allow microphone in browser settings.');
      } else {
        console.error('Recording error:', e);
        alert('Failed to start recording: ' + e.message);
      }
    }
  };

  const stop = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
    }
    setIsRecording(false);
    // activeField cleared in onstop after transcription
  };

  return { isRecording, isTranscribing, activeField, start, stop };
}


// ── Main Component ───────────────────────────────────────────────
function LogFood({ profile }) {
  const [step, setStep]               = useState(1);
  const [foodInput, setFoodInput]     = useState('');
  const [foodItems, setFoodItems]     = useState([]);
  const [workoutInput, setWorkoutInput] = useState('');
  const [weight, setWeight]           = useState(70);
  const [workoutData, setWorkoutData] = useState(null);
  const [caloriesBurned, setCaloriesBurned] = useState(0);
  const [notes, setNotes]             = useState('');
  const [loading, setLoading]         = useState(false);

  const { isRecording, isTranscribing, activeField, start, stop } = useAudioTranscription(API_URL);
  const navigate = useNavigate();

  // ── Transcribe Button ──────────────────────────────────────────
  const fieldSetters = { food: setFoodInput, workout: setWorkoutInput };

  const TranscribeButton = ({ field }) => {
    const active = isRecording && activeField === field;
    const transcribing = isTranscribing && activeField === field;

    if (transcribing) {
      return (
        <button type="button" className="btn btn-voice" disabled>
          ⏳&nbsp;Transcribing…
        </button>
      );
    }
    if (active) {
      return (
        <button
          type="button"
          onClick={stop}
          className="btn btn-voice recording"
          style={{
            background: '#ef4444',
            color: 'white',
            border: '2px solid #dc2626',
            animation: 'recordPulse 1.2s ease-in-out infinite',
          }}
        >
          ⏹&nbsp;Stop Recording
        </button>
      );
    }
    return (
      <button
        type="button"
        onClick={() => start(field, fieldSetters[field])}
        className="btn btn-voice"
        disabled={isRecording || isTranscribing}
      >
        🎙️&nbsp;Transcribe
      </button>
    );
  };

  const ListeningHint = ({ field }) => {
    if (isTranscribing && activeField === field)
      return <p style={{ color:'#888', fontSize:'13px', margin:'0 0 10px', textAlign:'center' }}>Sending audio to Whisper…</p>;
    if (isRecording && activeField === field)
      return <p style={{ color:'#ef4444', fontSize:'13px', margin:'0 0 10px', textAlign:'center', fontWeight:500 }}>
        🔴 Recording… speak clearly, then press <strong>Stop Recording</strong> when done
      </p>;
    return null;
  };

  // ── Food ───────────────────────────────────────────────────────
  const parseFood = async () => {
    if (!foodInput.trim()) { alert('Please enter what you ate'); return; }
    setLoading(true);
    try {
      const res = await axios.post(`${API_URL}/api/parse-food`, { food_description: foodInput });
      if (res.data.error) { alert('Error: ' + res.data.error); return; }
      setFoodItems(res.data.items);
      setStep(2);
    } catch (e) { alert('Error calculating macros'); }
    finally { setLoading(false); }
  };

  const confirmFood = () => setStep(3);
  const resetFood   = () => { setStep(1); setFoodInput(''); setFoodItems([]); };

  // ── Workout ────────────────────────────────────────────────────
  const calculateWorkout = async () => {
    if (!workoutInput.trim()) { skipWorkout(); return; }
    setLoading(true);
    try {
      const res = await axios.post(`${API_URL}/api/calculate-workout`, { workout_description: workoutInput, weight });
      if (res.data.error) { alert('Error: ' + res.data.error); return; }
      setWorkoutData(res.data);
      setCaloriesBurned(res.data.total_calories);
    } catch (e) { alert('Error calculating workout calories'); }
    finally { setLoading(false); }
  };

  const skipWorkout    = () => { setCaloriesBurned(0); setStep(4); };
  const confirmWorkout = () => setStep(4);

  // ── Save ───────────────────────────────────────────────────────
  const saveFoodLog = async () => {
    setLoading(true);
    try {
      const wCheck = await axios.get(`${API_URL}/api/check-weight-today`);
      let todayWeight = null;
      if (!wCheck.data.has_weight) {
        const w = prompt('Please enter your weight today (kg):');
        if (w) todayWeight = parseFloat(w);
      }
      const res = await axios.post(`${API_URL}/api/save-food-log`, {
        food_items: foodItems,
        workout_description: workoutInput,
        calories_burned: caloriesBurned,
        notes,
        weight: todayWeight,
      });
      if (res.data.success) { alert('✅ Food logged successfully!'); navigate('/'); }
    } catch (e) { alert('Error saving food log'); }
    finally { setLoading(false); }
  };

  const totalCals    = foodItems.reduce((s, i) => s + i.calories, 0);
  const totalProtein = foodItems.reduce((s, i) => s + i.protein,  0);
  const totalCarbs   = foodItems.reduce((s, i) => s + i.carbs,    0);
  const totalFats    = foodItems.reduce((s, i) => s + i.fats,     0);

  return (
    <div className="log-container">
      <style>{`
        @keyframes recordPulse {
          0%,100% { box-shadow: 0 0 0 0 rgba(239,68,68,0.5); }
          50%      { box-shadow: 0 0 0 8px rgba(239,68,68,0); }
        }
      `}</style>

      <h2>📝 Log Today's Food &amp; Workout</h2>

      {/* Step 1 */}
      {step === 1 && (
        <div className="card">
          <h3>Step 1: What did you eat?</h3>
          <p className="helper-text">Describe naturally or mention saved meals</p>
          <div className="form-group">
            <textarea
              rows="4"
              placeholder="I ate..."
              value={foodInput}
              onChange={(e) => setFoodInput(e.target.value)}
            />
          </div>
          <ListeningHint field="food" />
          <div className="voice-controls" style={{ gap:'3rem' }}>
            <TranscribeButton field="food" />
            <button onClick={parseFood} className="btn btn-primary" disabled={loading || isRecording}>
              {loading ? 'Calculating...' : 'Calculate Macros'}
            </button>
          </div>
        </div>
      )}

      {/* Step 2 */}
      {step === 2 && (
        <div className="card">
          <h3>Step 2: Review Calculated Macros</h3>
          <div className="food-items-display">
            {foodItems.map((item, idx) => (
              <div key={idx} className="food-review-item">
                <div className="food-review-header">
                  <strong>{item.food_name}</strong>
                  {item.is_saved_meal && <span className="badge">SAVED</span>}
                </div>
                <div className="food-review-macros">
                  <span>{Math.round(item.calories)} kcal</span>
                  <span>P: {item.protein.toFixed(1)}g</span>
                  <span>C: {item.carbs.toFixed(1)}g</span>
                  <span>F: {item.fats.toFixed(1)}g</span>
                </div>
                {item.notes && <div className="food-review-note">{item.notes}</div>}
              </div>
            ))}
          </div>
          <div className="totals-row">
            <div className="total-label">TOTAL:</div>
            <div className="total-values">
              <strong>{Math.round(totalCals)} kcal</strong> | P: {totalProtein.toFixed(1)}g |
              C: {totalCarbs.toFixed(1)}g | F: {totalFats.toFixed(1)}g
            </div>
          </div>
          <div className="button-group">
            <button onClick={confirmFood} className="btn btn-primary">Looks Good ✓</button>
            <button onClick={resetFood}   className="btn btn-secondary">Start Over</button>
          </div>
        </div>
      )}

      {/* Step 3 */}
      {step === 3 && (
        <div className="card">
          <h3>Step 3: Did you work out?</h3>
          <div className="form-group">
            <label>Workout Description (or leave empty to skip)</label>
            <textarea
              rows="3"
              placeholder="e.g., gym - legs 60min, 10min jog"
              value={workoutInput}
              onChange={(e) => setWorkoutInput(e.target.value)}
            />
          </div>
          <ListeningHint field="workout" />
          <div className="voice-controls" style={{ gap:'3rem', marginBottom:'1rem' }}>
            <TranscribeButton field="workout" />
          </div>
          <div className="form-group">
            <label>Your Weight (kg)</label>
            <input type="number" step="0.1" value={weight} onChange={(e) => setWeight(e.target.value)} />
          </div>
          {!workoutData ? (
            <div className="button-group">
              <button onClick={calculateWorkout} className="btn btn-primary" disabled={loading || isRecording}>
                {loading ? 'Calculating...' : 'Calculate Calories Burned'}
              </button>
              <button onClick={skipWorkout} className="btn btn-secondary">Skip Workout</button>
            </div>
          ) : (
            <div className="workout-result">
              <h4>Estimated Calories Burned: {Math.round(workoutData.total_calories)} kcal</h4>
              {workoutData.breakdown && (
                <div className="workout-breakdown">
                  {workoutData.breakdown.map((a, idx) => (
                    <div key={idx} className="workout-activity">
                      <span>{a.activity}</span>
                      <span>{a.duration_min} min → {Math.round(a.calories)} kcal</span>
                    </div>
                  ))}
                </div>
              )}
              {workoutData.notes && <p className="workout-note">{workoutData.notes}</p>}
              <button onClick={confirmWorkout} className="btn btn-primary">Confirm</button>
            </div>
          )}
        </div>
      )}

      {/* Step 4 */}
      {step === 4 && (
        <div className="card">
          <h3>Step 4: Any notes for today?</h3>
          <div className="form-group">
            <textarea rows="2" placeholder="Optional notes..." value={notes} onChange={(e) => setNotes(e.target.value)} />
          </div>
          <button onClick={saveFoodLog} className="btn btn-primary btn-large" disabled={loading}>
            {loading ? 'Saving...' : "💾 Save Today's Log"}
          </button>
        </div>
      )}
    </div>
  );
}

export default LogFood;
