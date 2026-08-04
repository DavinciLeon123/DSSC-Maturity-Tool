// frontend/src/components/layout/Footer.tsx
import logoWhite from '../../assets/logo-dssc-white.png';

export function Footer() {
  return (
    <footer
      style={{
        background: '#008ecf',
        color: 'rgba(255,255,255,0.7)',
        padding: '3rem 2rem 2rem',
        fontFamily: "'Jost', 'Helvetica Neue', Arial, sans-serif",
      }}
    >
      <div style={{ maxWidth: '1200px', margin: '0 auto' }}>
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'flex-start',
            flexWrap: 'wrap',
            gap: '2rem',
            marginBottom: '2rem',
          }}
        >
          {/* Brand column */}
          <div>
            <img src={logoWhite} alt="DSSC" style={{ height: '32px', marginBottom: '0.75rem', display: 'block' }} />
            <div
              style={{
                fontWeight: 600,
                fontSize: '1.1rem',
                color: 'white',
                marginBottom: '0.5rem',
              }}
            >
              DSSC
            </div>
            <div
              style={{
                fontSize: '0.875rem',
                color: 'rgba(255,255,255,0.6)',
                maxWidth: '280px',
                lineHeight: 1.6,
              }}
            >
              Data Spaces Support Centre
            </div>
          </div>

          {/* Links column */}
          <div style={{ display: 'flex', gap: '3rem', flexWrap: 'wrap' }}>
            <div>
              <div
                style={{
                  fontWeight: 600,
                  color: 'white',
                  marginBottom: '1rem',
                  fontSize: '0.875rem',
                }}
              >
                Links
              </div>
              <a
                href="mailto:info@dssc.eu"
                style={{
                  display: 'block',
                  color: 'rgba(255,255,255,0.6)',
                  textDecoration: 'none',
                  fontSize: '0.875rem',
                  marginBottom: '0.5rem',
                  fontFamily: "'Jost', 'Helvetica Neue', Arial, sans-serif",
                }}
              >
                Contact
              </a>
            </div>
          </div>
        </div>

        {/* Bottom bar */}
        <div
          style={{
            borderTop: '1px solid rgba(255,255,255,0.1)',
            paddingTop: '1.5rem',
            fontSize: '0.8125rem',
            color: 'rgba(255,255,255,0.4)',
          }}
        >
          &copy; {new Date().getFullYear()} DSSC. All rights reserved.
        </div>
      </div>
    </footer>
  );
}
