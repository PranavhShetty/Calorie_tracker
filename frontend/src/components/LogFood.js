import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { API_URL } from '../App';
import { useNavigate } from 'react-router-dom';

function LogFood({ profile }) {
  const [step, setStep] = useState(1);
  const [foodInput, setFoodInput] = useState('');
  const [foodItems, setFoodItems] = useState([]);
  const [workoutInput, setWorkoutInput] = useState('');
  const [weight, setWeight] = useState(70);
  const [workoutData, setWorkoutData] = useState(null);
  const [caloriesBurned, setCaloriesBurned] = useState(0);
  const [notes, setNotes] = useState('');
  const [loading, setLoading] = useState(false);
  
  // NEW: Voice recording states
  const [isRecording, setIsRecording] = useState(false);
  const [recognition, setRecognition] = useState(null);
  
  const navigate = useNavigate();

  // ADD THIS useEffect HERE (after state, before other functions)
  useEffect(() => {
    // Initialize speech recognition
    if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
      const recognitionInstance = new SpeechRecognition();
      
      recognitionInstance.continuous = false;
      recognitionInstance.interimResults = false;
      recognitionInstance.lang = 'en-IN'; // Indian English
      
      recognitionInstance.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        setFoodInput(prev => prev + ' ' + transcript);
        setIsRecording(false);
      };
      
      recognitionInstance.onerror = (event) => {
        console.error('Speech recognition error:', event.error);
        setIsRecording(false);
        if (event.error === 'not-allowed') {
          alert('Microphone access denied. Please enable microphone permissions.');
        }
      };
      
      recognitionInstance.onend = () => {
        setIsRecording(false);
      };
      
      setRecognition(recognitionInstance);
    }
  }, []);

  const startVoiceRecording = () => {
    if (!recognition) {
      alert('Speech recognition not supported in this browser. Please use Chrome or Edge.');
      return;
    }
    
    setIsRecording(true);
    recognition.start();
  };
  
  const stopVoiceRecording = () => {
    if (recognition) {
      recognition.stop();
      setIsRecording(false);
    }
  };

  const parseFood = async () => {
    if (!foodInput.trim()) {
      alert('Please enter what you ate');
      return;
    }

    setLoading(true);
    try {
      const response = await axios.post(`${API_URL}/api/parse-food`, {
        food_description: foodInput
      });

      if (response.data.error) {
        alert('Error: ' + response.data.error);
        return;
      }

      setFoodItems(response.data.items);
      setStep(2);
    } catch (error) {
      console.error('Error parsing food:', error);
      alert('Error calculating macros');
    } finally {
      setLoading(false);
    }
  };

  const confirmFood = () => {
    setStep(3);
  };

  const resetFood = () => {
    setStep(1);
    setFoodInput('');
    setFoodItems([]);
  };

  const calculateWorkout = async () => {
    if (!workoutInput.trim()) {
      skipWorkout();
      return;
    }

    setLoading(true);
    try {
      const response = await axios.post(`${API_URL}/api/calculate-workout`, {
        workout_description: workoutInput,
        weight: weight
      });

      if (response.data.error) {
        alert('Error: ' + response.data.error);
        return;
      }

      setWorkoutData(response.data);
      setCaloriesBurned(response.data.total_calories);
    } catch (error) {
      console.error('Error calculating workout:', error);
      alert('Error calculating workout calories');
    } finally {
      setLoading(false);
    }
  };

  const skipWorkout = () => {
    setCaloriesBurned(0);
    setStep(4);
  };

  const confirmWorkout = () => {
    setStep(4);
  };

const saveFoodLog = async () => {
  setLoading(true);
  
  // Check if weight was logged today
  try {
    const weightCheck = await axios.get(`${API_URL}/api/check-weight-today`);
    
    let todayWeight = null;
    if (!weightCheck.data.has_weight) {
      // Prompt for weight
      const weightInput = prompt('Please enter your weight today (kg):');
      if (weightInput) {
        todayWeight = parseFloat(weightInput);
      }
    }
    
    const response = await axios.post(`${API_URL}/api/save-food-log`, {
      food_items: foodItems,
      workout_description: workoutInput,
      calories_burned: caloriesBurned,
      notes: notes,
      weight: todayWeight  // Add weight to the payload
    });

    if (response.data.success) {
      alert('✅ Food logged successfully!');
      navigate('/');
    }
  } catch (error) {
    console.error('Error saving log:', error);
    alert('Error saving food log');
  } finally {
    setLoading(false);
  }
};

  const totalCals = foodItems.reduce((sum, item) => sum + item.calories, 0);
  const totalProtein = foodItems.reduce((sum, item) => sum + item.protein, 0);
  const totalCarbs = foodItems.reduce((sum, item) => sum + item.carbs, 0);
  const totalFats = foodItems.reduce((sum, item) => sum + item.fats, 0);

  return (
    <div className="log-container">
      <h2>📝 Log Today's Food & Workout</h2>

      {/* Step 1: Food Input */}
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

          <div className="voice-controls"style={{ gap: '3rem' }}>
            {!isRecording ? (
              <button 
                onClick={startVoiceRecording} 
                className="btn btn-voice"
                type="button"
              >
                🎙️ Transcribe
              </button>
            ) : (
              <button 
                onClick={stopVoiceRecording} 
                className="btn btn-voice recording"
                type="button"
              >
                <span className="recording-dot"></span>
                Recording...
              </button>
            )}
            
            <button onClick={parseFood} className="btn btn-primary" disabled={loading}>
              {loading ? 'Calculating...' : 'Calculate Macros'}
            </button>
          </div>
        </div>
      )}

      {/* Step 2: Review Food */}
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
              <strong>{Math.round(totalCals)} kcal</strong> |
              P: {totalProtein.toFixed(1)}g |
              C: {totalCarbs.toFixed(1)}g |
              F: {totalFats.toFixed(1)}g
            </div>
          </div>

          <div className="button-group">
            <button onClick={confirmFood} className="btn btn-primary">Looks Good ✓</button>
            <button onClick={resetFood} className="btn btn-secondary">Start Over</button>
          </div>
        </div>
      )}

     {/* Step 3: Workout Input */}
      {step === 3 && (
        <div className="card">
          <h3>Step 3: Did you work out?</h3>

          <div className="form-group">
            <label>Workout Description (or leave empty)</label>
            <textarea
              rows="3"
              placeholder="e.g., gym - legs 60min, 10min jog"
              value={workoutInput}
              onChange={(e) => setWorkoutInput(e.target.value)}
            />
          </div>

          <div className="voice-controls" style={{ gap: '3rem' }}>
            {!isRecording ? (
              <button 
                onClick={() => {
                  if (!recognition) {
                    alert('Speech recognition not supported');
                    return;
                  }
                  setIsRecording(true);
                  recognition.onresult = (event) => {
                    const transcript = event.results[0][0].transcript;
                    setWorkoutInput(prev => prev + ' ' + transcript);
                    setIsRecording(false);
                  };
                  recognition.start();
                }} 
                className="btn btn-voice"
                type="button"
              >
                🎙️ Transcribe
              </button>
            ) : (
              <button 
                onClick={stopVoiceRecording} 
                className="btn btn-voice recording"
                type="button"
              >
                <span className="recording-dot"></span>
                Recording...
              </button>
            )}
          </div>

          <div className="form-group">
            <label>Your Weight (kg)</label>
            <input
              type="number"
              step="0.1"
              value={weight}
              onChange={(e) => setWeight(e.target.value)}
            />
          </div>

          {!workoutData ? (
            <>
              <button onClick={calculateWorkout} className="btn btn-primary" disabled={loading}>
                {loading ? 'Calculating...' : 'Calculate Calories Burned'}
              </button>
              <button onClick={skipWorkout} className="btn btn-secondary">
                Skip Workout
              </button>
            </>
          ) : (
            <div className="workout-result">
              <h4>Estimated Calories Burned: {Math.round(workoutData.total_calories)} kcal</h4>
              {workoutData.breakdown && (
                <div className="workout-breakdown">
                  {workoutData.breakdown.map((activity, idx) => (
                    <div key={idx} className="workout-activity">
                      <span>{activity.activity}</span>
                      <span>{activity.duration_min} min → {Math.round(activity.calories)} kcal</span>
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

      {/* Step 4: Notes & Save */}
      {step === 4 && (
        <div className="card">
          <h3>Step 4: Any notes for today?</h3>

          <div className="form-group">
            <textarea
              rows="2"
              placeholder="Optional notes..."
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
            />
          </div>

          <button onClick={saveFoodLog} className="btn btn-primary btn-large" disabled={loading}>
            {loading ? 'Saving...' : '💾 Save Today\'s Log'}
          </button>
        </div>
      )}
    </div>
  );
}

export default LogFood;