// frontend/src/routes/index.tsx
import { createFileRoute, Link } from '@tanstack/react-router';
import { Footer } from '../components/layout/Footer';
import logoSrc from '../assets/logo-dssc-color.png';

export const Route = createFileRoute('/')({
  component: LandingPage,
});

function LandingPage() {
  return (
    <div
      style={{
        fontFamily: "'Jost', 'Helvetica Neue', Arial, sans-serif",
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
          style={{ height: '75px', width: 'auto' }}
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
              borderRadius: '0',
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
            background:
              'linear-gradient(135deg, rgba(118,184,42,0.06) 0%, rgba(0,142,207,0.10) 60%, rgba(255,255,255,0) 100%), #fff',
            padding: '6rem 2rem',
            textAlign: 'center',
          }}
        >
          <div style={{ maxWidth: '800px', margin: '0 auto' }}>
            <img src={logoSrc} alt="DSSC" style={{ height: '48px', marginBottom: '1.5rem' }} />
            <h1
              style={{
                fontSize: '2.75rem',
                fontWeight: 700,
                lineHeight: 1.2,
                marginBottom: '1.5rem',
                fontFamily: "'Jost', 'Helvetica Neue', Arial, sans-serif",
                color: '#1c2025',
              }}
            >
              <span style={{ background: 'linear-gradient(135deg, #76b82a 0%, #008ecf 100%)', WebkitBackgroundClip: 'text', backgroundClip: 'text', color: 'transparent', WebkitTextFillColor: 'transparent' }}>DSMA – Data Spaces Maturity Assessment</span>
            </h1>
            <p
              style={{
                fontSize: '1.1875rem',
                lineHeight: 1.7,
                marginBottom: '2.5rem',
                color: '#3d444b',
                maxWidth: '620px',
                margin: '0 auto 2.5rem',
              }}
            >
              A self-assessment tool that evaluates the maturity of a data space by
              answering a series of questions across key development indicators.
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
                  borderRadius: '0',
                  fontWeight: 600,
                  fontSize: '1rem',
                  textDecoration: 'none',
                  display: 'inline-block',
                }}
              >
                Start the assessment
              </Link>
              <Link
                to="/register"
                style={{
                  background: 'transparent',
                  color: '#008ecf',
                  padding: '1rem 2.5rem',
                  borderRadius: '0',
                  fontWeight: 600,
                  fontSize: '1rem',
                  textDecoration: 'none',
                  border: '1px solid rgba(0,142,207,0.4)',
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
                  title: 'Register your data space',
                  body: 'Create an account and register your Data Space (DS).',
                },
                {
                  step: '02',
                  title: 'Complete the assessment',
                  body: 'Work through the different maturity dimensions indicating your maturity within each question.',
                },
                {
                  step: '03',
                  title: 'Receive your report',
                  body: 'Generate an instant maturity report with your current levels.',
                },
              ].map(({ step, title, body }) => (
                <div
                  key={step}
                  style={{
                    background: 'white',
                    border: '1px solid rgba(118,184,42,0.3)',
                    borderRadius: '0',
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

        {/* Closing banner section */}
        <section
          style={{
            padding: '5rem 2rem',
            background:
              'linear-gradient(135deg, rgba(118,184,42,0.06) 0%, rgba(0,142,207,0.10) 60%, rgba(255,255,255,0) 100%), #fff',
          }}
        >
          <div
            style={{ maxWidth: '800px', margin: '0 auto', textAlign: 'center' }}
          >
            <h2
              style={{
                fontSize: '2rem',
                fontWeight: 700,
                color: '#1c2025',
                marginBottom: '1rem',
              }}
            >
              The DSMA gives you an immediate overview of your current maturity level.
            </h2>
            <p
              style={{
                fontSize: '1rem',
                color: '#3d444b',
                lineHeight: 1.8,
                marginBottom: '2rem',
              }}
            >
              Using the CEN / CENELEC Maturity Assessment standard, you will indicate what
              your current data space already has developed or where there is room for
              improvement.
            </p>
            <Link
              to="/login"
              style={{
                background: '#76b82a',
                color: 'white',
                padding: '0.875rem 2rem',
                borderRadius: '0',
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
