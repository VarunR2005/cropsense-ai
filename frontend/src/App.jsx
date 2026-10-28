import { Navigate, Route, Routes } from "react-router-dom";
import Layout from "./components/Layout.jsx";
import ProtectedRoute from "./components/ProtectedRoute.jsx";
import Landing from "./pages/Landing.jsx";
import Login from "./pages/Login.jsx";
import Register from "./pages/Register.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import YieldPrediction from "./pages/YieldPrediction.jsx";
import CropRecommendation from "./pages/CropRecommendation.jsx";
import FertilizerRecommendation from "./pages/FertilizerRecommendation.jsx";
import DiseaseDetection from "./pages/DiseaseDetection.jsx";
import WeatherForecast from "./pages/WeatherForecast.jsx";
import IrrigationPlanner from "./pages/IrrigationPlanner.jsx";
import Reports from "./pages/Reports.jsx";
import Profile from "./pages/Profile.jsx";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/yield" element={<YieldPrediction />} />
        <Route path="/crops" element={<CropRecommendation />} />
        <Route path="/fertilizer" element={<FertilizerRecommendation />} />
        <Route path="/disease" element={<DiseaseDetection />} />
        <Route path="/weather" element={<WeatherForecast />} />
        <Route path="/irrigation" element={<IrrigationPlanner />} />
        <Route path="/reports" element={<Reports />} />
        <Route path="/profile" element={<Profile />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
