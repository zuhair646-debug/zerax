import React from 'react';
import { Loader2, CheckCircle } from 'lucide-react';

const ProgressIndicator = ({ progress }) => {
  if (!progress) return null;

  const { step, status, message, percent } = progress;

  const getStepColor = () => {
    switch (status) {
      case 'analyzing': return 'border-blue-500 bg-blue-500/20';
      case 'processing': return 'border-purple-500 bg-purple-500/20';
      case 'generating': return 'border-orange-500 bg-orange-500/20';
      case 'complete': return 'border-green-500 bg-green-500/20';
      default: return 'border-gray-500 bg-gray-500/20';
    }
  };

  return (
    <div className="flex justify-end px-2 md:px-0 animate-fadeIn">
      <div className={`max-w-[85%] md:max-w-[70%] rounded-2xl p-4 border ${getStepColor()}`}>
        
        <div className="flex items-center gap-3 mb-3">
          <div className="p-2 rounded-full bg-white/10">
            {status === 'complete' ? (
              <CheckCircle className="w-5 h-5 text-green-400" />
            ) : (
              <Loader2 className="w-5 h-5 animate-spin text-white" />
            )}
          </div>
          <span className="font-medium text-white">{message}</span>
        </div>

        <div className="h-2 bg-slate-700 rounded-full overflow-hidden mb-3">
          <div 
            className={`h-full rounded-full transition-all duration-500 ${
              status === 'complete' ? 'bg-green-500' : 'bg-gradient-to-r from-purple-500 to-pink-500'
            }`}
            style={{ width: `${percent}%` }}
          />
        </div>

        <div className="flex justify-between text-xs">
          {['تحليل', 'معالجة', 'توليد', 'مكتمل'].map((label, i) => (
            <span 
              key={i}
              className={step > i ? 'text-white' : 'text-gray-500'}
            >
              {step > i ? '✅' : '⬜'} {label}
            </span>
          ))}
        </div>

        <div className="text-center mt-2">
          <span className="text-2xl font-bold text-white">{percent}%</span>
        </div>
      </div>
    </div>
  );
};

export default ProgressIndicator;
