import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { API_URL } from '../App';
import { getCache, setCache, invalidateCache } from '../apiCache';

function Meals({ profile }) {
  const [meals, setMeals] = useState([]);
  const [showModal, setShowModal] = useState(false);
  const [formData, setFormData] = useState({
    label: '',
    calories: '',
    protein: '',
    carbs: '',
    fats: '',
    aliases: '',
    description: ''
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchMeals();
  }, []);

  const fetchMeals = async () => {
    const cached = getCache('meals');
    if (cached) { setMeals(cached); setLoading(false); return; }
    try {
      const response = await axios.get(`${API_URL}/api/get-meals`);
      setCache('meals', response.data.meals || []);
      setMeals(response.data.meals || []);
    } catch (error) {
      console.error('Error fetching meals:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleInputChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    const aliases = formData.aliases
      ? formData.aliases.split(',').map(a => a.trim())
      : [];

    try {
      await axios.post(`${API_URL}/api/save-meal`, {
        label: formData.label,
        calories: parseFloat(formData.calories),
        protein: parseFloat(formData.protein),
        carbs: parseFloat(formData.carbs),
        fats: parseFloat(formData.fats),
        aliases: aliases,
        description: formData.description
      });

      alert('✅ Meal saved successfully!');
      setShowModal(false);
      setFormData({
        label: '',
        calories: '',
        protein: '',
        carbs: '',
        fats: '',
        aliases: '',
        description: ''
      });
      invalidateCache('meals');
      fetchMeals(); // Refresh list
    } catch (error) {
      console.error('Error saving meal:', error);
      alert('Error saving meal');
    }
  };

  const handleDelete = async (label) => {
    if (!window.confirm(`Delete "${label}"?`)) {
      return;
    }

    try {
      await axios.post(`${API_URL}/api/delete-meal`, { label });
      alert('✅ Meal deleted successfully!');
      invalidateCache('meals');
      fetchMeals(); // Refresh list
    } catch (error) {
      console.error('Error deleting meal:', error);
      alert('Error deleting meal');
    }
  };

  if (loading) {
    return <div className="loading"><div className="spinner"></div></div>;
  }

  return (
    <div className="meals-container">
      <div className="meals-header">
        <h2>📚 Your Saved Meals Library</h2>
        <button onClick={() => setShowModal(true)} className="btn btn-primary">
          + Add New Meal
        </button>
      </div>

      {meals.length > 0 ? (
        <div className="meals-grid">
          {meals.map((meal, idx) => (
            <div key={idx} className="meal-card">
              <div className="meal-header">
                <h3>{meal.label}</h3>
                <button onClick={() => handleDelete(meal.label)} className="btn-delete">
                  🗑️
                </button>
              </div>

              <div className="meal-macros">
                <div className="meal-macro">
                  <div className="macro-value">{Math.round(meal.calories)}</div>
                  <div className="macro-label">kcal</div>
                </div>
                <div className="meal-macro">
                  <div className="macro-value">{meal.protein.toFixed(1)}g</div>
                  <div className="macro-label">Protein</div>
                </div>
                <div className="meal-macro">
                  <div className="macro-value">{meal.carbs.toFixed(1)}g</div>
                  <div className="macro-label">Carbs</div>
                </div>
                <div className="meal-macro">
                  <div className="macro-value">{meal.fats.toFixed(1)}g</div>
                  <div className="macro-label">Fats</div>
                </div>
              </div>

              {meal.aliases && meal.aliases.length > 0 && (
                <div className="meal-aliases">
                  <strong>Also known as:</strong> {meal.aliases.join(', ')}
                </div>
              )}

              {meal.description && (
                <div className="meal-description">{meal.description}</div>
              )}
            </div>
          ))}
        </div>
      ) : (
        <div className="empty-state">
          <h3>No saved meals yet</h3>
          <p>Save your frequently eaten meals to log them instantly!</p>
          <button onClick={() => setShowModal(true)} className="btn btn-primary">
            Add Your First Meal
          </button>
        </div>
      )}

      {/* Add Meal Modal */}
      {showModal && (
        <div className="modal" onClick={() => setShowModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Add New Saved Meal</h3>
              <button onClick={() => setShowModal(false)} className="btn-close">
                ×
              </button>
            </div>

            <form onSubmit={handleSubmit}>
              <div className="form-group">
                <label>Meal Label *</label>
                <input
                  type="text"
                  name="label"
                  placeholder="e.g., Mum's dal rice"
                  value={formData.label}
                  onChange={handleInputChange}
                  required
                />
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label>Calories *</label>
                  <input
                    type="number"
                    name="calories"
                    step="0.1"
                    value={formData.calories}
                    onChange={handleInputChange}
                    required
                  />
                </div>
                <div className="form-group">
                  <label>Protein (g) *</label>
                  <input
                    type="number"
                    name="protein"
                    step="0.1"
                    value={formData.protein}
                    onChange={handleInputChange}
                    required
                  />
                </div>
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label>Carbs (g) *</label>
                  <input
                    type="number"
                    name="carbs"
                    step="0.1"
                    value={formData.carbs}
                    onChange={handleInputChange}
                    required
                  />
                </div>
                <div className="form-group">
                  <label>Fats (g) *</label>
                  <input
                    type="number"
                    name="fats"
                    step="0.1"
                    value={formData.fats}
                    onChange={handleInputChange}
                    required
                  />
                </div>
              </div>

              <div className="form-group">
                <label>Aliases (comma separated)</label>
                <input
                  type="text"
                  name="aliases"
                  placeholder="e.g., mom's dal rice, dal chawal"
                  value={formData.aliases}
                  onChange={handleInputChange}
                />
              </div>

              <div className="form-group">
                <label>Description</label>
                <textarea
                  name="description"
                  rows="2"
                  placeholder="What's in this meal?"
                  value={formData.description}
                  onChange={handleInputChange}
                />
              </div>

              <div className="modal-footer">
                <button type="submit" className="btn btn-primary">
                  Save Meal
                </button>
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="btn btn-secondary"
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

export default Meals;