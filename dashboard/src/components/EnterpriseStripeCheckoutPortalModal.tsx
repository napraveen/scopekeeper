import React, { useState } from 'react';
import { CheckCircle2, Sparkles } from 'lucide-react';

export const EnterpriseStripeCheckoutPortalModal: React.FC<{ isOpen: boolean; onClose: () => void }> = ({ isOpen, onClose }) => {
  const [active, setActive] = useState(false);
  if (!isOpen) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6 text-white max-w-md w-full shadow-2xl">
        <div className="flex items-center justify-between pb-3 border-b border-zinc-800 mb-4">
          <div className="flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-indigo-400" />
            <h3 className="font-bold text-lg">Enterprise Stripe Checkout Portal</h3>
          </div>
          <span className="text-xs bg-indigo-500/20 text-indigo-300 px-2 py-0.5 rounded font-mono font-semibold">CR-007</span>
        </div>
        
        {active ? (
          <div className="text-center py-6">
            <CheckCircle2 className="w-12 h-12 text-emerald-400 mx-auto mb-3" />
            <p className="font-bold text-lg">Work Order Complete ($1,620)</p>
            <p className="text-xs text-zinc-400 mt-1">Authorized under SOW v1.2 Scope Amendment</p>
            <button onClick={onClose} className="mt-5 px-4 py-2 bg-zinc-800 hover:bg-zinc-700 rounded-lg text-sm font-medium w-full transition">
              Close Preview
            </button>
          </div>
        ) : (
          <div>
            <div className="bg-zinc-800/50 p-4 rounded-lg border border-zinc-700/50 mb-4">
              <div className="flex justify-between text-sm mb-1.5">
                <span className="text-zinc-400">Authorized Value:</span>
                <span className="font-bold text-emerald-400">$1,620.00</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-zinc-400">Implementation SLA:</span>
                <span className="font-medium text-zinc-200">+2 business days</span>
              </div>
            </div>
            
            <p className="text-sm text-zinc-300 mb-5 leading-relaxed">
              This module implements <strong>Enterprise Stripe Checkout Portal</strong> authorized by Dhana (Head of Product) via ScopeKeeper Telegram.
            </p>
            
            <div className="flex gap-2">
              <button onClick={onClose} className="flex-1 py-2 bg-zinc-800 hover:bg-zinc-700 rounded-lg text-sm text-zinc-300">
                Dismiss
              </button>
              <button onClick={() => setActive(true)} className="flex-1 py-2 bg-indigo-600 hover:bg-indigo-500 rounded-lg text-sm font-semibold text-white shadow-lg shadow-indigo-500/20">
                Activate CR-007
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
