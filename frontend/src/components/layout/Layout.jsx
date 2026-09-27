import Navbar from './Navbar';
import Footer from './Footer';
import './Layout.css';

function Layout({ children }) {
  return (
    <div className="app-layout">
      <Navbar />
      <main className="app-content">{children}</main>
      <Footer />
    </div>
  );
}

export default Layout;