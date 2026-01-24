/**
 * T03: SoftPullCard Component
 *
 * FCRA consent UI component for soft-pull credit authorization.
 * Per tasks/T03_credit_flow.md
 */

import React, { useState } from 'react';
import './SoftPullCard.css';

interface SoftPullCardProps {
  onConsent: () => void;
  onCancel: () => void;
  dealerName: string;
  isLoading?: boolean;
}

const SoftPullCard: React.FC<SoftPullCardProps> = ({
  onConsent,
  onCancel,
  dealerName,
  isLoading = false
}) => {
  const [acknowledged, setAcknowledged] = useState(false);

  const handleConsent = () => {
    if (acknowledged) {
      onConsent();
    }
  };

  return (
    <div className="soft-pull-card">
      <div className="soft-pull-header">
        <span className="soft-pull-icon">🔒</span>
        <h3>Credit Pre-Qualification</h3>
      </div>

      <div className="soft-pull-content">
        <p className="consent-intro">
          To check your financing options, we need your authorization to perform
          a <strong>soft credit inquiry</strong>.
        </p>

        <div className="consent-box">
          <p className="consent-text">
            I understand that by clicking 'I Agree', I am providing 'written
            instructions' under the Fair Credit Reporting Act (FCRA) authorizing{' '}
            <strong>{dealerName}</strong> to obtain personal credit information
            from one or more consumer reporting agencies solely for
            pre-qualification purposes.
          </p>
          <p className="consent-highlight">
            <strong>This will not affect my credit score.</strong>
          </p>
        </div>

        <label className="consent-checkbox">
          <input
            type="checkbox"
            checked={acknowledged}
            onChange={(e) => setAcknowledged(e.target.checked)}
            disabled={isLoading}
          />
          <span>I have read and understand the above authorization</span>
        </label>
      </div>

      <div className="soft-pull-actions">
        <button
          className="btn-primary"
          onClick={handleConsent}
          disabled={!acknowledged || isLoading}
        >
          {isLoading ? 'Processing...' : 'I Agree'}
        </button>
        <button
          className="btn-secondary"
          onClick={onCancel}
          disabled={isLoading}
        >
          Cancel
        </button>
      </div>

      <p className="soft-pull-disclaimer">
        By clicking "I Agree", you acknowledge that your IP address and timestamp
        will be recorded for compliance purposes.
      </p>
    </div>
  );
};

export default SoftPullCard;
