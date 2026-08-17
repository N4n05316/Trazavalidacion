import { BrowserRouter, Route, Routes } from "react-router-dom";
import { AuthProvider, useAuth } from "./auth/AuthContext";
import { Layout } from "./components/Layout";
import { CenterMessage } from "./components/CenterMessage";
import { Login } from "./pages/Login";
import { Dashboard } from "./pages/Dashboard";
import { Casos } from "./pages/Casos";
import { BalanceMasa } from "./pages/BalanceMasa";
import { Declaraciones } from "./pages/Declaraciones";
import { Cruce } from "./pages/Cruce";
import { Ingesta } from "./pages/Ingesta";
import { Usuarios } from "./pages/Usuarios";
import { Waves } from "lucide-react";

function Gate() {
  const { loading, usuario } = useAuth();

  if (loading) {
    return <CenterMessage icon={Waves} title="Cargando Certus…" />;
  }
  if (!usuario) {
    return <Login />;
  }

  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Dashboard />} />
        <Route path="casos" element={<Casos />} />
        <Route path="balance-masa" element={<BalanceMasa />} />
        <Route path="declaraciones" element={<Declaraciones />} />
        <Route path="cruce" element={<Cruce />} />
        <Route path="ingesta" element={<Ingesta />} />
        <Route path="usuarios" element={<Usuarios />} />
      </Route>
    </Routes>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Gate />
      </AuthProvider>
    </BrowserRouter>
  );
}
