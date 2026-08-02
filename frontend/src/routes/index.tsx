// frontend/src/routes/index.tsx
import { createFileRoute, Link } from '@tanstack/react-router';
import { Footer } from '../components/layout/Footer';
import logoSrc from '../assets/logo-dssc-color.png';
import logoWhite from '../assets/logo-dssc-white.png';

export const Route = createFileRoute('/')({
  component: LandingPage,
});

function LandingPage() {
  return (
    <div
      style={{
        fontFamily: "'Open Sans', sans-serif",
        background: 'white',
        minHeight: '100vh',
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      {/* Public nav header */}
      <header
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '0 2rem',
          height: '64px',
          background: '#ffffff',
          borderBottom: '1px solid rgba(0,142,207,0.08)',
        }}
      >
        <img
          src={logoSrc}
          alt="DSSC"
          style={{ width: '76px', height: 'auto' }}
        />
        <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
          <Link
            to="/login"
            style={{
              color: '#008ecf',
              textDecoration: 'none',
              fontWeight: 500,
              fontSize: '0.9375rem',
            }}
          >
            Log In
          </Link>
          <Link
            to="/register"
            style={{
              background: '#76b82a',
              color: 'white',
              padding: '0.5rem 1.25rem',
              borderRadius: '8px',
              textDecoration: 'none',
              fontWeight: 600,
              fontSize: '0.9375rem',
            }}
          >
            Register
          </Link>
        </div>
      </header>

      <main style={{ flex: 1 }}>
        {/* Hero section */}
        <section
          style={{
            background: 'linear-gradient(135deg, #008ecf 0%, #008ecf 100%)',
            color: 'white',
            padding: '6rem 2rem',
            textAlign: 'center',
          }}
        >
          <div style={{ maxWidth: '800px', margin: '0 auto' }}>
            <img src={logoWhite} alt="DSSC" style={{ height: '48px', marginBottom: '1.5rem' }} />
            <h1
              style={{
                fontSize: '2.75rem',
                fontWeight: 700,
                lineHeight: 1.2,
                marginBottom: '1.5rem',
                fontFamily: "'Open Sans', sans-serif",
              }}
            >
              DSSC Maturity Scan for Dataspaces
            </h1>
            <p
              style={{
                fontSize: '1.1875rem',
                lineHeight: 1.7,
                marginBottom: '2.5rem',
                color: 'rgba(255,255,255,0.85)',
                maxWidth: '620px',
                margin: '0 auto 2.5rem',
              }}
            >
              A practical self-assessment tool that helps you understand and
              improve the interoperability of your initiative
            </p>
            <div
              style={{
                display: 'flex',
                gap: '1rem',
                justifyContent: 'center',
                flexWrap: 'wrap',
              }}
            >
              <Link
                to="/login"
                style={{
                  background: '#76b82a',
                  color: 'white',
                  padding: '1rem 2.5rem',
                  borderRadius: '8px',
                  fontWeight: 600,
                  fontSize: '1rem',
                  textDecoration: 'none',
                  display: 'inline-block',
                }}
              >
                Start the check
              </Link>
              <Link
                to="/register"
                style={{
                  background: 'transparent',
                  color: 'white',
                  padding: '1rem 2.5rem',
                  borderRadius: '8px',
                  fontWeight: 600,
                  fontSize: '1rem',
                  textDecoration: 'none',
                  border: '1px solid rgba(255,255,255,0.4)',
                  display: 'inline-block',
                }}
              >
                Create an account
              </Link>
            </div>
          </div>
        </section>

        {/* How does it work section */}
        <section style={{ padding: '5rem 2rem', background: 'white' }}>
          <div style={{ maxWidth: '1100px', margin: '0 auto' }}>
            <h2
              style={{
                textAlign: 'center',
                fontSize: '2rem',
                fontWeight: 700,
                color: '#008ecf',
                marginBottom: '3rem',
              }}
            >
              How does it work?
            </h2>
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
                gap: '1.5rem',
              }}
            >
              {[
                {
                  step: '01',
                  title: 'Register your initiative',
                  body: 'Create an account and register your Data Sharing Initiative (DSI) or Service Provider (SP) initiative.',
                },
                {
                  step: '02',
                  title: 'Complete the assessment',
                  body: 'Work through the structured Dataspace Maturity Assessment with a 1-5 maturity score per question.',
                },
                {
                  step: '03',
                  title: 'Receive your report',
                  body: 'Generate an instant interoperability heatmap with your current compliance level.',
                },
              ].map(({ step, title, body }) => (
                <div
                  key={step}
                  style={{
                    background: 'white',
                    border: '1px solid rgba(118,184,42,0.3)',
                    borderRadius: '16px',
                    padding: '2rem',
                    boxShadow: '0 2px 12px rgba(0,142,207,0.06)',
                  }}
                >
                  <div
                    style={{
                      width: '40px',
                      height: '40px',
                      background: 'rgba(118,184,42,0.12)',
                      borderRadius: '8px',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      color: '#76b82a',
                      fontWeight: 700,
                      fontSize: '0.875rem',
                      marginBottom: '1.25rem',
                    }}
                  >
                    {step}
                  </div>
                  <h3
                    style={{
                      fontSize: '1.125rem',
                      fontWeight: 600,
                      color: '#008ecf',
                      marginBottom: '0.75rem',
                    }}
                  >
                    {title}
                  </h3>
                  <p
                    style={{
                      fontSize: '0.9375rem',
                      color: 'rgba(0,142,207,0.65)',
                      lineHeight: 1.6,
                    }}
                  >
                    {body}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* MAMI section */}
        <section
          style={{
            padding: '5rem 2rem',
            background:
              'linear-gradient(90deg, rgba(118,184,42,0.07) 0%, rgba(118,184,42,0.07) 100%), white',
          }}
        >
          <div
            style={{ maxWidth: '800px', margin: '0 auto', textAlign: 'center' }}
          >
            <h2
              style={{
                fontSize: '2rem',
                fontWeight: 700,
                color: '#008ecf',
                marginBottom: '1rem',
              }}
            >
              The Dataspace Maturity Assessment gives you an immediate overview of your
              current level of dataspace maturity.
            </h2>
            <p
              style={{
                fontSize: '1rem',
                color: 'rgba(0,142,207,0.7)',
                lineHeight: 1.8,
                marginBottom: '2rem',
              }}
            >
              Across six categories (Governance, Business, Legal, Interoperability, Control over Data &amp; Trust, and Value Creation),
              you will rate your current maturity level. Your answers are visualised in a clear maturity radar.
            </p>
            <Link
              to="/login"
              style={{
                background: '#76b82a',
                color: 'white',
                padding: '0.875rem 2rem',
                borderRadius: '8px',
                fontWeight: 600,
                fontSize: '1rem',
                textDecoration: 'none',
                display: 'inline-block',
              }}
            >
              Get started
            </Link>
          </div>
        </section>
      </main>

      <Footer />
    </div>
  );
}
