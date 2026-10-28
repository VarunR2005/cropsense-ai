import { Navigate } from "react-router-dom";
import { useAuth } from "../services/auth.jsx";
import Spinner from "./Spinner.jsx";

export default function ProtectedRoute({ children }) {
  const { user, loading } = useAuth();
  if (loading) return <Spinner label="Checking your session..." />;
  if (!user) return <Navigate to="/login" replace />;
  return children;
}
