import React from 'react';
import type { AgentStatus } from '../hooks/useJarvisSocket';
import { useAudioVisualizer } from '../hooks/useAudioVisualizer';
import type { AgentPersonaId } from '../types/agent';
import { AGENT_PERSONAS } from '../types/agent';

interface AudioVisualizerProps {
  status: AgentStatus;
  persona?: AgentPersonaId;
  barCount?: number;
}

export const AudioVisualizer: React.FC<AudioVisualizerProps> = ({
  status,
  persona = 'jarvis',
  barCount = 48
}) => {
  const frequencies = useAudioVisualizer(status, barCount);
  const personaConfig = AGENT_PERSONAS[persona] || AGENT_PERSONAS.jarvis;

  const getBarColor = (height: number) => {
    if (status === 'thinking') {
      return height > 60
        ? 'bg-amber-300 shadow-[0_0_12px_#fde047]'
        : 'bg-amber-500/80';
    }
    if (status === 'speaking' || status === 'listening') {
      if (persona === 'ultron') {
        return height > 50
          ? 'bg-purple-300 shadow-[0_0_12px_#d8b4fe]'
          : 'bg-purple-500';
      }
      if (persona === 'friday') {
        return height > 50
          ? 'bg-emerald-200 shadow-[0_0_12px_#6ee7b7]'
          : 'bg-emerald-400';
      }
      if (persona === 'vision') {
        return height > 50
          ? 'bg-lime-200 shadow-[0_0_12px_#a3e635]'
          : 'bg-lime-400';
      }
      if (persona === 'karen') {
        return height > 50
          ? 'bg-pink-200 shadow-[0_0_12px_#f472b6]'
          : 'bg-pink-400';
      }
      if (persona === 'titan') {
        return height > 50
          ? 'bg-orange-200 shadow-[0_0_12px_#fb923c]'
          : 'bg-orange-400';
      }
      return height > 50
        ? 'bg-cyan-200 shadow-[0_0_12px_#a5f3fc]'
        : 'bg-cyan-400';
    }
    return 'bg-cyan-900/40';
  };

  return (
    <div
      className="relative flex flex-col items-center justify-center w-full px-3 sm:px-6 py-2 sm:py-3 bg-gray-950/80 backdrop-blur-md border rounded-xl sm:rounded-2xl transition-all duration-300 shadow-lg"
      style={{
        borderColor: `${personaConfig.color}40`,
        boxShadow: status === 'speaking' || status === 'listening' ? `0 0 25px ${personaConfig.color}25` : 'none'
      }}
    >
      {/* Visualizer Header */}
      <div className="flex items-center justify-between w-full mb-1.5 px-1">
        <div className="flex items-center space-x-1.5 sm:space-x-2">
          <span className="w-1.5 sm:w-2 h-1.5 sm:h-2 rounded-full animate-pulse" style={{ backgroundColor: personaConfig.color }} />
          <span
            className="font-mono text-[9px] sm:text-[10px] uppercase font-bold tracking-wider sm:tracking-widest transition-colors truncate max-w-[150px] sm:max-w-none"
            style={{ color: personaConfig.color }}
          >
            {personaConfig.name} // AUDIO STREAM
          </span>
        </div>
        <span className="font-mono text-[8px] sm:text-[10px] text-slate-400 font-bold uppercase tracking-wider">
          {status === 'speaking'
            ? '● TRANSMITTING'
            : status === 'listening'
            ? '● LISTENING'
            : status === 'thinking'
            ? '● PROCESSING'
            : '○ STANDBY'}
        </span>
      </div>

      {/* Waveform Bar Container */}
      <div className="flex items-center justify-center space-x-1 sm:space-x-1.5 w-full h-10 sm:h-14 md:h-16 px-1 sm:px-2">
        {frequencies.map((height, index) => (
          <div
            key={index}
            className="flex-1 max-w-[6px] sm:max-w-[8px] rounded-full transition-all duration-75"
            style={{
              height: `${Math.max(8, height)}%`,
            }}
          >
            <div className={`w-full h-full rounded-full transition-colors duration-200 ${getBarColor(height)}`} />
          </div>
        ))}
      </div>
    </div>
  );
};
