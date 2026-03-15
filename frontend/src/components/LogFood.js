import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { API_URL } from '../App';
import { useNavigate, useSearchParams } from 'react-router-dom';

// ── Audio Transcription Hook (MediaRecorder → Groq Whisper) ──────
function useAudioTranscription(apiUrl) {
  const [isRecording, setIsRecording]       = useState(false);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [activeField, setActiveField]       = useState(null);

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
      chunksRef.current = [];
      onTextRef.current = onText;
      fieldRef.current  = field;

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
          const res  = await fetch(`${apiUrl}/api/transcribe`, { method: 'POST', body: formData, credentials: 'include' });
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
  };

  return { isRecording, isTranscribing, activeField, start, stop };
}


// ── Main Component ───────────────────────────────────────────────
function LogFood({ profile }) {
  // Read ?date=YYYY-MM-DD from the URL (set by Week.js Edit buttons)
  const [searchParams] = useSearchParams();
  const dateParam  = searchParams.get('date');
  const today      = new Date().toISOString().split('T')[0];
  const logDate    = dateParam || today;
  const isEditMode = Boolean(dateParam);  // true when editing a past day

  const [step, setStep]                       = useState(isEditMode ? 2 : 1); // edit mode starts at step 2
  const [initLoading, setInitLoading]         = useState(isEditMode);         // loading existing entries

  const [foodInput, setFoodInput]             = useState('');
  const [foodItems, setFoodItems]             = useState([]);
  const [editingIdx, setEditingIdx]           = useState(null);
  const [showAddMore, setShowAddMore]         = useState(false);  // "Add More Items" panel in edit mode
  const [addMoreInput, setAddMoreInput]       = useState('');
  const [addMoreLoading, setAddMoreLoading]   = useState(false);

  const [workoutInput, setWorkoutInput]       = useState('');
  const [weight, setWeight]                   = useState(70);
  const [workoutData, setWorkoutData]         = useState(null);
  const [caloriesBurned, setCaloriesBurned]   = useState(0);
  const [notes, setNotes]                     = useState('');
  const [weightToday, setWeightToday]         = useState('');
  const [hasWeightToday, setHasWeightToday]   = useState(false);
  const [loading, setLoading]                 = useState(false);
  const [error, setError]                     = useState('');

  const { isRecording, isTranscribing, activeField, start, stop } = useAudioTranscription(API_URL);
  const navigate = useNavigate();

  // ── Edit mode: load existing entries on mount ──────────────────
  // When the user clicks "Edit" on the Week view, we fetch their existing
  // food entries for that date and pre-populate step 2.
  useEffect(() => {
    if (!isEditMode) return;
    axios.get(`${API_URL}/api/food-entries-for-date?date=${logDate}`)
      .then(res => {
        setFoodItems(res.data.food_entries || []);
        const s = res.data.summary;
        if (s) {
          setWorkoutInput(s.workout_description || '');
          setCaloriesBurned(s.calories_burned || 0);
          setNotes(s.notes || '');
        }
      })
      .catch(() => setError('Failed to load existing log'))
      .finally(() => setInitLoading(false));
  }, [isEditMode, logDate]);

  // ── Check if weight already logged when reaching step 4 ───────
  useEffect(() => {
    if (step === 4) {
      axios.get(`${API_URL}/api/check-weight-today`)
        .then(res => setHasWeightToday(res.data.has_weight))
        .catch(() => {});
    }
  }, [step]);

  // ── Transcribe Button ──────────────────────────────────────────
  const fieldSetters = { food: setFoodInput, workout: setWorkoutInput, addMore: setAddMoreInput };

  const TranscribeButton = ({ field }) => {
    const active       = isRecording && activeField === field;
    const transcribing = isTranscribing && activeField === field;
    if (transcribing) {
      return <button type="button" className="btn btn-voice" disabled>⏳&nbsp;Transcribing…</button>;
    }
    if (active) {
      return (
        <button
          type="button"
          onClick={stop}
          className="btn btn-voice recording"
          style={{ background: '#ef4444', color: 'white', border: '2px solid #dc2626', animation: 'recordPulse 1.2s ease-in-out infinite' }}
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
      return <p style={{ color: '#888', fontSize: '13px', margin: '0 0 10px', textAlign: 'center' }}>Sending audio to Whisper…</p>;
    if (isRecording && activeField === field)
      return <p style={{ color: '#ef4444', fontSize: '13px', margin: '0 0 10px', textAlign: 'center', fontWeight: 500 }}>
        🔴 Recording… speak clearly, then press <strong>Stop Recording</strong> when done
      </p>;
    return null;
  };

  // ── Inline macro editing ───────────────────────────────────────
  const updateFoodItem = (idx, field, value) => {
    setFoodItems(prev =>
      prev.map((item, i) =>
        i === idx ? { ...item, [field]: parseFloat(value) || 0 } : item
      )
    );
  };

  // ── Remove an item from the list ──────────────────────────────
  // Removes by index. Uses filter() to create a new array without that item.
  const removeItem = (idx) => {
    setFoodItems(prev => prev.filter((_, i) => i !== idx));
    if (editingIdx === idx) setEditingIdx(null);
  };

  // ── Add more items via LLM (edit mode "Add More" panel) ───────
  const parseAndAdd = async () => {
    if (!addMoreInput.trim()) return;
    setAddMoreLoading(true);
    setError('');
    try {
      const res = await axios.post(`${API_URL}/api/parse-food`, { food_description: addMoreInput });
      if (res.data.error) { setError('Error: ' + res.data.error); return; }
      // Append new items to existing list
      setFoodItems(prev => [...prev, ...res.data.items]);
      setAddMoreInput('');
      setShowAddMore(false);
    } catch (e) {
      setError('Error calculating macros. Please try again.');
    } finally {
      setAddMoreLoading(false);
    }
  };

  // ── Food (Step 1 → Step 2) ─────────────────────────────────────
  const parseFood = async () => {
    if (!foodInput.trim()) { setError('Please enter what you ate'); return; }
    setError('');
    setLoading(true);
    try {
      const res = await axios.post(`${API_URL}/api/parse-food`, { food_description: foodInput });
      if (res.data.error) { setError('Error: ' + res.data.error); return; }
      setFoodItems(res.data.items);
      setStep(2);
    } catch (e) {
      setError('Error calculating macros. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const confirmFood = () => { setEditingIdx(null); setShowAddMore(false); setStep(3); };
  const resetFood   = () => { setStep(1); setFoodInput(''); setFoodItems([]); setEditingIdx(null); setError(''); };

  // ── Workout ────────────────────────────────────────────────────
  const calculateWorkout = async () => {
    if (!workoutInput.trim()) { skipWorkout(); return; }
    setError('');
    setLoading(true);
    try {
      const res = await axios.post(`${API_URL}/api/calculate-workout`, { workout_description: workoutInput, weight });
      if (res.data.error) { setError('Error: ' + res.data.error); return; }
      setWorkoutData(res.data);
      setCaloriesBurned(res.data.total_calories);
    } catch (e) {
      setError('Error calculating workout calories');
    } finally {
      setLoading(false);
    }
  };

  const skipWorkout    = () => { setCaloriesBurned(0); setStep(4); };
  const confirmWorkout = () => setStep(4);

  // ── Save ───────────────────────────────────────────────────────
  const saveFoodLog = async () => {
    if (foodItems.length === 0) { setError('No food items to save'); return; }
    setLoading(true);
    setError('');
    try {
      if (isEditMode) {
        // Edit mode: save to specific date (backend deletes old entries first)
        await axios.post(`${API_URL}/api/save-specific-day-log`, {
          log_date:            logDate,
          food_items:          foodItems,
          workout_description: workoutInput,
          calories_burned:     caloriesBurned,
          notes,
        });
        navigate('/week');
      } else {
        // New log: save to today (handles weight logging too)
        await axios.post(`${API_URL}/api/save-food-log`, {
          food_items:          foodItems,
          workout_description: workoutInput,
          calories_burned:     caloriesBurned,
          notes,
          weight: !hasWeightToday && weightToday ? parseFloat(weightToday) : null,
        });
        navigate('/');
      }
    } catch (e) {
      const msg = e?.response?.data?.error || e?.message || 'Unknown error';
      setError(`Error saving food log: ${msg}`);
    } finally {
      setLoading(false);
    }
  };

  const totalCals    = foodItems.reduce((s, i) => s + i.calories, 0);
  const totalProtein = foodItems.reduce((s, i) => s + i.protein,  0);
  const totalCarbs   = foodItems.reduce((s, i) => s + i.carbs,    0);
  const totalFats    = foodItems.reduce((s, i) => s + i.fats,     0);

  // Show spinner while loading existing entries (edit mode only)
  if (initLoading) {
    return <div className="loading"><div className="spinner" /></div>;
  }

  return (
    <div className="log-container">
      <style>{`
        @keyframes recordPulse {
          0%,100% { box-shadow: 0 0 0 0 rgba(239,68,68,0.5); }
          50%      { box-shadow: 0 0 0 8px rgba(239,68,68,0); }
        }
      `}</style>

      <h2>
        {isEditMode ? `✏️ Editing Log — ${logDate}` : '📝 Log Today\'s Food & Workout'}
      </h2>

      {/* Inline error banner */}
      {error && (
        <div className="error-banner">
          <span>{error}</span>
          <button onClick={() => setError('')} className="error-close">×</button>
        </div>
      )}

      {/* ── Step 1: Describe food (new log only) ──────────────── */}
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
          <div className="voice-controls" style={{ gap: '3rem' }}>
            <TranscribeButton field="food" />
            <button onClick={parseFood} className="btn btn-primary" disabled={loading || isRecording}>
              {loading ? 'Calculating...' : 'Calculate Macros'}
            </button>
          </div>
        </div>
      )}

      {/* ── Step 2: Review + edit items ───────────────────────── */}
      {step === 2 && (
        <div className="card">
          <h3>{isEditMode ? 'Edit Food Items' : 'Step 2: Review Calculated Macros'}</h3>
          <p className="helper-text">
            Tap an item to edit its macros&nbsp;·&nbsp;
            <span style={{ color: '#ef4444' }}>✕</span> to remove it
          </p>

          <div className="food-items-display">
            {foodItems.length === 0 && (
              <p style={{ color: '#64748b', textAlign: 'center', padding: '16px 0' }}>
                No items yet — add some below
              </p>
            )}
            {foodItems.map((item, idx) => (
              <div
                key={idx}
                className={`food-review-item${editingIdx === idx ? ' food-review-item-editing' : ''}`}
                onClick={() => setEditingIdx(editingIdx === idx ? null : idx)}
              >
                <div className="food-review-header">
                  <strong>{item.food_name}</strong>
                  <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                    {item.is_saved_meal && <span className="badge">SAVED</span>}
                    <span className="edit-hint">{editingIdx === idx ? '▲' : '✏️'}</span>
                    {/* Remove button — stopPropagation so it doesn't also toggle edit */}
                    <button
                      className="remove-item-btn"
                      onClick={e => { e.stopPropagation(); removeItem(idx); }}
                      title="Remove item"
                    >
                      ✕
                    </button>
                  </div>
                </div>

                {editingIdx !== idx && (
                  <div className="food-review-macros">
                    <span>{Math.round(item.calories)} kcal</span>
                    <span>P: {item.protein.toFixed(1)}g</span>
                    <span>C: {item.carbs.toFixed(1)}g</span>
                    <span>F: {item.fats.toFixed(1)}g</span>
                  </div>
                )}

                {editingIdx === idx && (
                  <div
                    className="inline-edit-grid"
                    onClick={e => e.stopPropagation()}
                  >
                    {[
                      { label: 'Calories', field: 'calories', unit: 'kcal' },
                      { label: 'Protein',  field: 'protein',  unit: 'g' },
                      { label: 'Carbs',    field: 'carbs',    unit: 'g' },
                      { label: 'Fats',     field: 'fats',     unit: 'g' },
                    ].map(({ label, field, unit }) => (
                      <div key={field} className="inline-edit-field">
                        <label className="inline-edit-label">{label}</label>
                        <div className="inline-edit-input-row">
                          <input
                            type="number"
                            step="0.1"
                            min="0"
                            value={item[field]}
                            onChange={e => updateFoodItem(idx, field, e.target.value)}
                            className="inline-edit-input"
                          />
                          <span className="inline-edit-unit">{unit}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                {item.notes && <div className="food-review-note">{item.notes}</div>}
              </div>
            ))}
          </div>

          {/* Totals row */}
          {foodItems.length > 0 && (
            <div className="totals-row">
              <div className="total-label">TOTAL:</div>
              <div className="total-values">
                <strong>{Math.round(totalCals)} kcal</strong> | P: {totalProtein.toFixed(1)}g |
                C: {totalCarbs.toFixed(1)}g | F: {totalFats.toFixed(1)}g
              </div>
            </div>
          )}

          {/* Add More Items panel — visible in both modes */}
          {showAddMore ? (
            <div className="add-more-panel">
              <p className="helper-text" style={{ marginBottom: 8 }}>Describe the extra food to add:</p>
              <div className="form-group" style={{ marginBottom: 8 }}>
                <textarea
                  rows="2"
                  placeholder="e.g., 1 banana, protein shake"
                  value={addMoreInput}
                  onChange={e => setAddMoreInput(e.target.value)}
                />
              </div>
              <ListeningHint field="addMore" />
              <div className="voice-controls" style={{ gap: '1rem' }}>
                <TranscribeButton field="addMore" />
                <button
                  onClick={parseAndAdd}
                  className="btn btn-primary"
                  disabled={addMoreLoading || !addMoreInput.trim()}
                >
                  {addMoreLoading ? 'Calculating...' : '+ Add'}
                </button>
                <button
                  onClick={() => { setShowAddMore(false); setAddMoreInput(''); }}
                  className="btn btn-secondary"
                >
                  Cancel
                </button>
              </div>
            </div>
          ) : (
            <button
              onClick={() => setShowAddMore(true)}
              className="btn btn-secondary"
              style={{ width: '100%', marginTop: 8 }}
            >
              + Add More Items
            </button>
          )}

          <div className="button-group" style={{ marginTop: 16 }}>
            <button onClick={confirmFood} className="btn btn-primary" disabled={foodItems.length === 0}>
              {isEditMode ? 'Continue →' : 'Looks Good ✓'}
            </button>
            {!isEditMode && (
              <button onClick={resetFood} className="btn btn-secondary">Start Over</button>
            )}
          </div>
        </div>
      )}

      {/* ── Step 3: Workout ───────────────────────────────────── */}
      {step === 3 && (
        <div className="card">
          <h3>{isEditMode ? 'Edit Workout' : 'Step 3: Did you work out?'}</h3>
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
          <div className="voice-controls" style={{ gap: '3rem', marginBottom: '1rem' }}>
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

      {/* ── Step 4: Final details ─────────────────────────────── */}
      {step === 4 && (
        <div className="card">
          <h3>{isEditMode ? 'Save Changes' : 'Step 4: Final Details'}</h3>

          {/* Weight input only for today's new log, not for editing past days */}
          {!isEditMode && !hasWeightToday && (
            <div className="form-group">
              <label>Your Weight Today (kg) <span style={{ color: '#64748b', fontWeight: 400 }}>— optional</span></label>
              <input
                type="number"
                step="0.1"
                min="0"
                placeholder="e.g. 72.5"
                value={weightToday}
                onChange={e => setWeightToday(e.target.value)}
              />
              <p className="helper-text">Used to track your weight trend over time</p>
            </div>
          )}

          <div className="form-group">
            <label>Notes <span style={{ color: '#64748b', fontWeight: 400 }}>— optional</span></label>
            <textarea
              rows="2"
              placeholder="e.g. cheat day, not feeling well..."
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
            />
          </div>

          <button onClick={saveFoodLog} className="btn btn-primary btn-large" disabled={loading}>
            {loading ? 'Saving...' : isEditMode ? '💾 Save Changes' : "💾 Save Today's Log"}
          </button>
        </div>
      )}
    </div>
  );
}

export default LogFood;
