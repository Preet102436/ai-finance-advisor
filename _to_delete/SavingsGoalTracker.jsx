import { useEffect, useState } from "react";
import {
  allocateToGoal,
  createSavingsGoal,
  deleteSavingsGoal,
  fetchAvailableToAllocate,
  fetchSavingsGoals,
} from "../lib/savings";

const EMPTY_GOAL = { label: "", targetAmount: "", targetDate: "" };

function SettingsGearIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <circle cx="12" cy="12" r="3" stroke="currentColor" strokeWidth="1.6" />
      <path
        d="M12 3V5.2M12 18.8V21M21 12H18.8M5.2 12H3M18.0 6.0L16.5 7.5M7.5 16.5L6.0 18.0M18.0 18.0L16.5 16.5M7.5 7.5L6.0 6.0"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
      />
    </svg>
  );
}

export default function SavingsGoalTracker() {
  const [goals, setGoals] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [pool, setPool] = useState(null);
  const [poolError, setPoolError] = useState("");

  const [showForm, setShowForm] = useState(false);
  const [newGoal, setNewGoal] = useState(EMPTY_GOAL);
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState("");

  // Which goal's gear menu is open, and which goal has the allocate form open.
  const [openMenuId, setOpenMenuId] = useState(null);
  const [allocatingGoalId, setAllocatingGoalId] = useState(null);
  const [allocateAmount, setAllocateAmount] = useState("");
  const [allocateError, setAllocateError] = useState("");
  const [allocating, setAllocating] = useState(false);

  function loadPool() {
    fetchAvailableToAllocate()
      .then(setPool)
      .catch((err) => setPoolError(err.message || "Failed to load available income"));
  }

  function load() {
    setLoading(true);
    setError("");
    fetchSavingsGoals()
      .then(setGoals)
      .catch((err) => setError(err.message || "Failed to load savings goals"))
      .finally(() => setLoading(false));
    loadPool();
  }

  useEffect(() => {
    load();
  }, []);

  function openAllocateForm(goalId) {
    setOpenMenuId(null);
    setAllocatingGoalId(goalId);
    setAllocateAmount("");
    setAllocateError("");
  }

  async function submitAllocation(goalId, sign) {
    const raw = parseFloat(allocateAmount);
    if (Number.isNaN(raw) || raw <= 0) {
      setAllocateError("Enter an amount greater than 0.");
      return;
    }
    setAllocating(true);
    setAllocateError("");
    try {
      await allocateToGoal(goalId, raw * sign);
      setAllocatingGoalId(null);
      setAllocateAmount("");
      load();
    } catch (err) {
      setAllocateError(err.message || "Failed to update allocation");
    } finally {
      setAllocating(false);
    }
  }

  async function handleCreate(e) {
    e.preventDefault();
    const amount = parseFloat(newGoal.targetAmount);
    if (Number.isNaN(amount) || amount <= 0) {
      setCreateError("Enter a target amount greater than 0.");
      return;
    }
    if (!newGoal.targetDate) {
      setCreateError("Pick a target date.");
      return;
    }
    setCreating(true);
    setCreateError("");
    try {
      await createSavingsGoal({ targetAmount: amount, targetDate: newGoal.targetDate, label: newGoal.label.trim() });
      setNewGoal(EMPTY_GOAL);
      setShowForm(false);
      load();
    } catch (err) {
      setCreateError(err.message || "Failed to create savings goal");
    } finally {
      setCreating(false);
    }
  }

  async function handleDelete(goalId, label) {
    const ok = window.confirm(`Delete the "${label || "Savings goal"}" goal? This can't be undone.`);
    if (!ok) return;
    try {
      await deleteSavingsGoal(goalId);
      load();
    } catch (err) {
      setError(err.message || "Failed to delete savings goal");
    }
  }

  return (
    <div>
      <div className="section-title-row">
        <div>
          <h2 className="section-title">Savings goals</h2>
          <p className="section-subtitle">
            Allocate money to a goal yourself from what's available below - progress is
            whatever you've manually set aside, not an automatic guess from your transactions.
          </p>
        </div>
        <button type="button" className="btn btn-secondary btn-small" onClick={() => setShowForm((v) => !v)}>
          {showForm ? "Cancel" : "+ New goal"}
        </button>
      </div>

      {poolError && <p className="status-banner status-error">{poolError}</p>}
      {pool && (
        <div className="available-pool-banner">
          <div className="available-pool-label">
            Available to allocate (net income minus what's already allocated to your goals)
          </div>
          <div className="available-pool-amount">${pool.available_to_allocate.toFixed(2)}</div>
        </div>
      )}

      {showForm && (
        <form className="add-transaction-card" onSubmit={handleCreate}>
          <div className="form-row">
            <label>
              Goal name (optional)
              <input
                type="text"
                value={newGoal.label}
                onChange={(e) => setNewGoal({ ...newGoal, label: e.target.value })}
                placeholder="e.g. Europe trip"
              />
            </label>
            <label>
              Target amount
              <input
                type="number"
                step="0.01"
                min="0.01"
                value={newGoal.targetAmount}
                onChange={(e) => setNewGoal({ ...newGoal, targetAmount: e.target.value })}
                placeholder="5000.00"
                required
              />
            </label>
            <label>
              Target date
              <input
                type="date"
                value={newGoal.targetDate}
                onChange={(e) => setNewGoal({ ...newGoal, targetDate: e.target.value })}
                required
              />
            </label>
          </div>
          <span className="field-hint">
            Only income and expenses dated from today onward count toward this goal, so pick a
            target date in the future.
          </span>
          {createError && <p className="status-banner status-error">{createError}</p>}
          <button type="submit" className="btn" disabled={creating}>
            {creating ? "Creating..." : "Create goal"}
          </button>
        </form>
      )}

      {loading && <p>Loading savings goals...</p>}
      {error && <p className="status-banner status-error">{error}</p>}
      {!loading && !error && (
        goals.length === 0 ? (
          <p className="empty-state">
            No savings goals yet - click "+ New goal" to set a target amount and date. Progress
            will track itself from your real transactions after that.
          </p>
        ) : (
          <div className="cards-grid">
            {goals.map((g) => {
              const savedDisplay = Math.max(0, g.allocated_amount);
              return (
                <div key={g.goal_id} className="budget-card">
                  <div className="budget-card-header">
                    <span className="budget-card-category">{g.label || "Savings goal"}</span>
                    <div className="card-menu-wrap">
                      <button
                        type="button"
                        className="card-menu-trigger"
                        onClick={() => setOpenMenuId(openMenuId === g.goal_id ? null : g.goal_id)}
                        aria-label="Goal settings"
                        title="Allocate money or delete this goal"
                      >
                        <SettingsGearIcon />
                      </button>
                      {openMenuId === g.goal_id && (
                        <div className="card-menu">
                          <button type="button" onClick={() => openAllocateForm(g.goal_id)}>
                            Allocate money
                          </button>
                          <button
                            type="button"
                            className="card-menu-danger"
                            onClick={() => {
                              setOpenMenuId(null);
                              handleDelete(g.goal_id, g.label);
                            }}
                          >
                            Delete goal
                          </button>
                        </div>
                      )}
                    </div>
                  </div>
                  <div className="meter-track">
                    <div
                      className="meter-fill"
                      style={{
                        width: `${Math.min(g.progress_pct, 100)}%`,
                        background: g.on_track === false ? "var(--color-warning)" : "var(--color-success)",
                      }}
                    />
                  </div>
                  <div className="budget-card-amounts">
                    <span>${savedDisplay.toFixed(2)} allocated</span>
                    <span className="budget-card-limit">of ${g.target_amount.toFixed(2)} by {g.target_date}</span>
                  </div>
                  <div className="goal-status-row">
                    <span className="goal-progress-pct">{g.progress_pct.toFixed(0)}% there</span>
                    {g.on_track === false && (
                      <span className="goal-status-badge goal-status-behind">Behind pace</span>
                    )}
                    {g.on_track === true && (
                      <span className="goal-status-badge goal-status-ontrack">On track</span>
                    )}
                  </div>
                  {allocatingGoalId === g.goal_id && (
                    <div className="card-inline-form">
                      <span className="field-hint">
                        {pool ? `$${pool.available_to_allocate.toFixed(2)} available right now.` : ""}
                      </span>
                      <div className="card-inline-form-row">
                        <input
                          type="number"
                          step="0.01"
                          min="0.01"
                          placeholder="Amount"
                          value={allocateAmount}
                          onChange={(e) => setAllocateAmount(e.target.value)}
                        />
                        <button
                          type="button"
                          className="btn btn-small"
                          disabled={allocating}
                          onClick={() => submitAllocation(g.goal_id, 1)}
                        >
                          Add to goal
                        </button>
                        <button
                          type="button"
                          className="btn btn-secondary btn-small"
                          disabled={allocating}
                          onClick={() => submitAllocation(g.goal_id, -1)}
                        >
                          Withdraw
                        </button>
                        <button
                          type="button"
                          className="btn btn-secondary btn-small"
                          onClick={() => setAllocatingGoalId(null)}
                        >
                          Close
                        </button>
                      </div>
                      {allocateError && <p className="status-banner status-error">{allocateError}</p>}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )
      )}
    </div>
  );
}
