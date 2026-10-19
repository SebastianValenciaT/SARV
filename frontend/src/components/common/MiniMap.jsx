import Icon from './Icon';
import './MiniMap.css';

/**
 * MiniMap: mapa ilustrativo pequeño con un pin centrado.
 * Placeholder visual hasta integrar un proveedor de mapas real.
 */
function MiniMap({ icon = 'alert', className = '' }) {
  return (
    <div className={`minimap ${className}`.trim()}>
      <svg viewBox="0 0 380 280" preserveAspectRatio="xMidYMid slice" aria-hidden="true">
        <rect width="380" height="280" fill="#EEEFF1" />
        <path d="M170 0h120l90 70v70l-100-20-60-60z" fill="#CFE2B8" />
        <path d="M300 280l-30-70 110-20v90z" fill="#CFE2B8" />
        <path d="M-10 70C60 60 70 130 40 170S60 250 40 290" stroke="#C9D8F2" strokeWidth="22" fill="none" />
        <path
          d="M-10 140L120 150 220 120 400 60"
          stroke="#F4CB75"
          strokeWidth="9"
          fill="none"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        <path d="M70 280L130 150 190 0" stroke="#F4CB75" strokeWidth="9" fill="none" strokeLinecap="round" />
        <g stroke="#fff" strokeWidth="6" fill="none" strokeLinecap="round">
          <path d="M0 220L400 190" />
          <path d="M250 0L300 280" />
          <path d="M130 150L380 235" />
        </g>
      </svg>
      <div className="minimap-pin">
        <Icon name={icon} />
      </div>
    </div>
  );
}

export default MiniMap;
