'use client';

import { GoogleOAuthProvider, GoogleLogin } from '@react-oauth/google';

const CLIENT_ID = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID || '';

interface Props {
  onSuccess: (credential: string) => void;
  onError: () => void;
}

export default function GoogleSignIn({ onSuccess, onError }: Props) {
  if (!CLIENT_ID) {
    return (
      <div className="text-xs text-gray-500 text-center py-2">Google sign-in not configured</div>
    );
  }

  return (
    <GoogleOAuthProvider clientId={CLIENT_ID}>
      <GoogleLogin
        onSuccess={(credResp) => {
          if (credResp.credential) {
            onSuccess(credResp.credential);
          } else {
            onError();
          }
        }}
        onError={() => onError()}
        theme="filled_black"
        size="large"
        width={320}
        text="continue_with"
        shape="rectangular"
      />
    </GoogleOAuthProvider>
  );
}
