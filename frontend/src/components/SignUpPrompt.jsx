export default function SignUpPrompt({ onSignUp, onDismiss }) {
  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(0,0,0,0.75)',
        zIndex: 50,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '1.5rem',
      }}
    >
      <div
        style={{
          background: '#111',
          border: '1px solid #222',
          borderRadius: '2px',
          padding: '2rem',
          maxWidth: '320px',
          width: '100%',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          textAlign: 'center',
        }}
      >
        <p style={{
          color: '#c8873a',
          fontSize: '0.65rem',
          letterSpacing: '0.15em',
          marginBottom: '0.75rem',
        }}>
          ENJOYING YOUR JOURNEY?
        </p>

        <h2 style={{
          fontSize: '1.1rem',
          fontWeight: '600',
          letterSpacing: '0.05em',
          marginBottom: '0.75rem',
        }}>
          Save your discoveries
        </h2>

        <p style={{
          color: '#555',
          fontSize: '0.75rem',
          lineHeight: 1.6,
          marginBottom: '1.5rem',
        }}>
          Create a free account to keep your journey history,
          continue where you left off, and share with others.
        </p>

        <button
          onClick={onSignUp}
          style={{
            width: '100%',
            padding: '0.75rem',
            background: '#c8873a',
            border: 'none',
            borderRadius: '2px',
            color: '#0a0a0a',
            fontSize: '0.75rem',
            fontWeight: '600',
            letterSpacing: '0.12em',
            cursor: 'pointer',
            marginBottom: '1rem',
          }}
        >
          CREATE FREE ACCOUNT
        </button>

        <button
          onClick={onDismiss}
          style={{
            background: 'none',
            border: 'none',
            color: '#444',
            fontSize: '0.7rem',
            letterSpacing: '0.08em',
            cursor: 'pointer',
            padding: '0.25rem',
          }}
        >
          Keep listening as guest
        </button>
      </div>
    </div>
  );
}
