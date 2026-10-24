import { createContext } from "react";
import type { AuthPayload, User } from "../types/auth";

export interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: (payload: AuthPayload) => Promise<void>;
  register: (payload: AuthPayload) => Promise<void>;
  logout: () => void;
}

// Defined in its own file so AuthContext.tsx (which exports AuthProvider)
// satisfies the react/only-export-components lint rule.
export const AuthContext = createContext<AuthContextType | undefined>(undefined);
