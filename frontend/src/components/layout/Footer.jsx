import { Link } from 'react-router-dom';
import './Footer.css';

function Footer() {
  const year = new Date().getFullYear();

  return (
    <footer className="footer">
      <div className="footer-container">
        <p className="footer-text">
          © {year} SARV — Sistema de Atención y Reportes Viales
        </p>
        <Link to="/aviso-privacidad" className="footer-link">
          Aviso de privacidad
        </Link>
      </div>
    </footer>
  );
}

export default Footer;