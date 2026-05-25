const { useEffect, useMemo, useState } = React;

const api = async (url, options = {}) => {
  const res = await fetch(url, {
    credentials: "same-origin",
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
    body: options.body ? JSON.stringify(options.body) : undefined,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || "No se pudo completar la accion.");
  return data;
};

const money = (n) => new Intl.NumberFormat("es-CO", { style: "currency", currency: "COP", maximumFractionDigits: 0 }).format(n || 0);
const prettyDate = (v) => (v ? new Date(v).toLocaleString("es-CO") : "Sin fecha");
const datetimeLocal = (v) => {
  if (!v) return "";
  const d = new Date(v);
  const pad = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
};
const tabLabel = (value) => ({ inicio: "Inicio", admin: "Admin", agenda: "Agenda", historial: "Historial", reservas: "Reservas", ofertas: "Ofertas", perfil: "Perfil", mensajes: "Mensajes", notificaciones: "Notificaciones" }[value] || value);
const finishedReservations = (items = []) => items.filter((r) => r.status === "finalizado");
const agendaReservations = (items = []) => items.filter((r) => ["pendiente", "aceptado", "prestando"].includes(r.status));
const statusLabel = (status) => ({ pendiente: "Pendiente", aceptado: "Aceptada", prestando: "Prestando servicio", finalizado: "Finalizado", cancelado: "Cancelado", rechazado: "Rechazado" }[status] || status);
const actionLabel = (status) => ({ aceptado: "Aceptar", prestando: "Iniciar", finalizado: "Finalizar", rechazado: "Rechazar" }[status] || statusLabel(status));
const providerStatusActions = (r) => {
  if (r.status === "pendiente") return ["aceptado", "rechazado"];
  if (r.status === "aceptado") return ["prestando", "rechazado"];
  if (r.status === "prestando") return ["finalizado"];
  return [];
};
const serviceSteps = (r) => [
  { key: "aceptado", label: "Aceptada", done: ["aceptado", "prestando", "finalizado"].includes(r.status) },
  { key: "prestando", label: "Prestando servicio", done: ["prestando", "finalizado"].includes(r.status) },
  { key: "finalizado", label: "Finalizado", done: r.status === "finalizado" },
  { key: "pago", label: "Pago", done: r.is_paid },
  { key: "calificaciones", label: "Calificaciones", done: r.client_rated && r.provider_rated },
  { key: "terminado", label: "Terminado", done: r.workflow_status === "Terminado" },
];

function App() {
  const [session, setSession] = useState(null);
  const [data, setData] = useState(null);
  const [tab, setTab] = useState("inicio");
  const [error, setError] = useState("");

  const load = async () => {
    setError("");
    const s = await api("/api/session/");
    setSession(s);
    if (s.authenticated) setData(await api("/api/bootstrap/"));
  };

  useEffect(() => { load().catch((e) => setError(e.message)); }, []);

  const run = async (fn) => {
    try {
      setError("");
      await fn();
      await load();
    } catch (e) {
      setError(e.message);
    }
  };

  if (!session) return <div className="main">Cargando...</div>;
  if (!session.authenticated) return <Auth onDone={load} error={error} setError={setError} />;
  if (!data) return <div className="main">Cargando datos...</div>;

  const profile = data?.profile || session.profile;
  const tabs = profile.role === "admin"
    ? ["inicio", "admin", "agenda", "ofertas", "reservas", "notificaciones"]
    : ["inicio", "agenda", "historial", "reservas", "ofertas", "perfil", "mensajes", "notificaciones"];
  const openTab = (nextTab) => {
    setTab(nextTab);
    if (["agenda", "reservas", "historial"].includes(nextTab)) {
      load().catch((e) => setError(e.message));
    }
  };

  return (
    <div className="shell">
      <header className="topbar">
        <div className="brand">
          <strong>La Casa al Dia</strong>
          <span>{profile.full_name} · {profile.role} · {profile.status}</span>
        </div>
        <nav className="nav">
          {tabs.map((t) => <button key={t} className={tab === t ? "active" : ""} onClick={() => openTab(t)}>{tabLabel(t)}</button>)}
          <button className="secondary" onClick={() => run(() => api("/api/logout/", { method: "POST" }))}>Salir</button>
        </nav>
      </header>
      <main className="main">
        {error && <div className="notice error">{error}</div>}
        {tab === "inicio" && <Home profile={profile} data={data} run={run} setTab={setTab} />}
        {tab === "agenda" && <Agenda profile={profile} data={data} run={run} refresh={() => load().catch((e) => setError(e.message))} />}
        {tab === "historial" && <History profile={profile} data={data} run={run} />}
        {tab === "reservas" && <Reservations profile={profile} data={data} run={run} />}
        {tab === "ofertas" && <Offers profile={profile} data={data} run={run} setTab={setTab} />}
        {tab === "perfil" && <ProfileEditor profile={profile} data={data} run={run} />}
        {tab === "mensajes" && <Messages run={run} />}
        {tab === "notificaciones" && <Notifications data={data} run={run} />}
        {tab === "admin" && <AdminPanel run={run} />}
      </main>
    </div>
  );
}

function Auth({ onDone, error, setError }) {
  const [mode, setMode] = useState("login");
  const [form, setForm] = useState({ role: "cliente", email: "", password: "", first_name: "", last_name: "", city: "Bogota" });
  const [message, setMessage] = useState("");
  const submit = async (e) => {
    e.preventDefault();
    try {
      setError("");
      setMessage("");
      const result = await api(mode === "login" ? "/api/login/" : "/api/register/", { method: "POST", body: form });
      if (result.pending_approval) {
        setMessage(result.message || "Tu registro quedo pendiente de aprobacion.");
        setMode("login");
        return;
      }
      await onDone();
    } catch (err) {
      setError(err.message);
    }
  };
  return (
    <div className="auth">
      <section className="hero">
        <div>
          <h1>La Casa al Dia</h1>
          <p>Servicios domesticos y lavanderia con perfiles verificados, agenda, pagos, calificaciones, ofertas y control administrativo.</p>
        </div>
      </section>
      <form className="auth-panel" onSubmit={submit}>
        <h2>{mode === "login" ? "Iniciar sesion" : "Crear cuenta"}</h2>
        {error && <div className="notice error">{error}</div>}
        {message && <div className="notice">{message}</div>}
        {mode === "register" && (
          <div className="grid two">
            <Field label="Nombres" value={form.first_name} onChange={(v) => setForm({ ...form, first_name: v })} />
            <Field label="Apellidos" value={form.last_name} onChange={(v) => setForm({ ...form, last_name: v })} />
            <label>Rol<select value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })}><option value="cliente">Cliente</option><option value="ov">Oficios varios</option><option value="lavanderia">Lavanderia</option><option value="admin">Administrador</option></select></label>
            <Field label="Ciudad" value={form.city} onChange={(v) => setForm({ ...form, city: v })} />
            <Field label="Barrio" value={form.neighborhood || ""} onChange={(v) => setForm({ ...form, neighborhood: v })} />
            <Field label="Direccion" value={form.address || ""} onChange={(v) => setForm({ ...form, address: v })} />
            <Field label="Documento" value={form.document_id || ""} onChange={(v) => setForm({ ...form, document_id: v })} />
            <Field label="Telefono" value={form.phone || ""} onChange={(v) => setForm({ ...form, phone: v })} />
          </div>
        )}
        <Field label="Correo" type="email" value={form.email} onChange={(v) => setForm({ ...form, email: v })} />
        <Field label="Contrasena" type="password" value={form.password} onChange={(v) => setForm({ ...form, password: v })} />
        <button>{mode === "login" ? "Entrar" : "Registrarme"}</button>
        <button type="button" className="secondary" onClick={() => setMode(mode === "login" ? "register" : "login")}>
          {mode === "login" ? "Crear una cuenta" : "Ya tengo cuenta"}
        </button>
        <div className="notice">Demo: admin@lcd.com/admin123, cliente@lcd.com/cliente123, oficios@lcd.com/oficios123, lavanderia@lcd.com/lav123</div>
      </form>
    </div>
  );
}

function Home({ profile, data, run, setTab }) {
  const stats = useMemo(() => ({
    reservas: data.reservations?.length || 0,
    ofertas: data.offers?.length || 0,
    pagos: data.payments?.length || 0,
    pendientes: data.notifications?.filter((n) => !n.read).length || 0,
  }), [data]);
  return (
    <section className="section">
      <div className="hero">
        <div>
          <h1>{profile.role === "admin" ? "Control total del sistema" : "Tu agenda domestica en orden"}</h1>
          <p>Gestiona reservas, ofertas, postulaciones, pagos, mensajes, calificaciones y notificaciones desde un solo lugar.</p>
        </div>
      </div>
      {profile.status === "pendiente" && <div className="notice">Tu perfil esta pendiente de aprobacion. Puedes editar tu informacion mientras administracion revisa tus datos.</div>}
      <div className="stat-grid">
        <Stat label="Reservas" value={stats.reservas} />
        <Stat label="Ofertas" value={stats.ofertas} />
        <Stat label="Pagos" value={stats.pagos} />
        <Stat label="Notificaciones" value={stats.pendientes} />
      </div>
      <div className="row">
        <button onClick={() => setTab("reservas")}>Gestionar reservas</button>
        <button className="secondary" onClick={() => setTab("agenda")}>Ver agenda</button>
        <button className="secondary" onClick={() => setTab("ofertas")}>Ver ofertas</button>
        {profile.role === "admin" && <button onClick={() => setTab("admin")}>Panel admin</button>}
      </div>
    </section>
  );
}

function Agenda({ profile, data, run, refresh }) {
  const items = agendaReservations(data.reservations).sort((a, b) => new Date(a.scheduled_for) - new Date(b.scheduled_for));
  return (
    <section className="section">
      <div className="section-head">
        <h2>Agenda</h2>
        <div className="row">
          <span className="pill">{items.length} servicios activos</span>
          <button className="secondary" onClick={refresh}>Actualizar</button>
        </div>
      </div>
      <div className="agenda-board">
        {items.length === 0 && <div className="notice">No tienes servicios agendados, aceptados o en prestacion.</div>}
        {items.map((r) => <AgendaBlock key={r.id} r={r} profile={profile} run={run} />)}
      </div>
    </section>
  );
}

function AgendaBlock({ r, profile, run }) {
  const counterpart = profile.id === r.client.id ? r.provider : r.client;
  const canProviderUpdate = r.provider.id === profile.id;
  const actions = canProviderUpdate ? providerStatusActions(r) : [];
  return (
    <article className={`agenda-block status-${r.status}`}>
      <div className="date-box">
        <b>{new Date(r.scheduled_for).toLocaleDateString("es-CO", { day: "2-digit", month: "short" })}</b>
        <span>{new Date(r.scheduled_for).toLocaleTimeString("es-CO", { hour: "2-digit", minute: "2-digit" })}</span>
      </div>
      <div>
        <h3>{r.service.name}</h3>
        <p className="muted">{counterpart.full_name} · {r.modality} · {money(r.total)}</p>
        <p className="muted">{r.workflow_status}</p>
        <p>{r.address}</p>
      </div>
      <div className="agenda-actions">
        <span className="pill">{statusLabel(r.status)}</span>
        {actions.map((s) => (
          <button
            key={s}
            className={s === "rechazado" ? "warning" : "secondary"}
            onClick={() => run(() => api(`/api/reservations/${r.id}/status/`, { method: "POST", body: { status: s } }))}
          >
            {actionLabel(s)}
          </button>
        ))}
      </div>
    </article>
  );
}

function History({ profile, data, run }) {
  const items = finishedReservations(data.reservations).sort((a, b) => new Date(b.scheduled_for) - new Date(a.scheduled_for));
  return (
    <section className="section">
      <div className="section-head"><h2>Historial</h2><span className="pill">{items.length} servicios realizados</span></div>
      <div className="cards">
        {items.length === 0 && <div className="notice">Aun no tienes servicios finalizados.</div>}
        {items.map((r) => <HistoryCard key={r.id} r={r} profile={profile} run={run} />)}
      </div>
    </section>
  );
}

function Reservations({ profile, data, run }) {
  const [form, setForm] = useState({ service_id: "", scheduled_for: "", modality: "domicilio", address: profile.address || "", notes: "" });
  const selected = data.services.find((s) => String(s.id) === String(form.service_id));
  return (
    <section className="section">
      <div className="section-head"><h2>Reservas</h2><span className="pill">{data.reservations.length} registros</span></div>
      {profile.role === "cliente" && (
        <form className="card grid two" onSubmit={(e) => { e.preventDefault(); run(() => api("/api/reservations/", { method: "POST", body: form })); }}>
          <label>Servicio<select required value={form.service_id} onChange={(e) => setForm({ ...form, service_id: e.target.value })}><option value="">Seleccionar</option>{data.services.map((s) => <option key={s.id} value={s.id}>{s.name} - {s.provider_name} - {money(s.price)}</option>)}</select></label>
          <Field label="Fecha y hora" type="datetime-local" value={form.scheduled_for} onChange={(v) => setForm({ ...form, scheduled_for: v })} />
          <label>Modalidad<select value={form.modality} onChange={(e) => setForm({ ...form, modality: e.target.value })}><option value="domicilio">Domicilio</option><option value="punto_fisico">Punto fisico</option></select></label>
          <Field label="Direccion" value={form.address} onChange={(v) => setForm({ ...form, address: v })} />
          <label>Notas<textarea value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} /></label>
          <button disabled={!selected}>Reservar {selected ? money(selected.price) : ""}</button>
        </form>
      )}
      <div className="cards">
        {data.reservations.map((r) => <ReservationCard key={r.id} r={r} profile={profile} run={run} />)}
      </div>
    </section>
  );
}

function ReservationCard({ r, profile, run }) {
  const canProvider = r.provider.id === profile.id;
  const canClient = r.client.id === profile.id;
  const canPay = canClient && !r.is_paid && r.status !== "cancelado" && r.status !== "rechazado";
  const [paying, setPaying] = useState(false);
  return (
    <article className="card">
      <div className="row"><h3>{r.service.name}</h3><span className="pill">{r.workflow_status || statusLabel(r.status)}</span></div>
      <div className="muted">{prettyDate(r.scheduled_for)} · {r.modality} · {money(r.total)}</div>
      <div>Cliente: {r.client.full_name}</div>
      <div>Prestador: {r.provider.full_name}</div>
      <div>{r.address}</div>
      <div className="muted">Pago: {r.is_paid ? "Pagado" : "Pendiente"}</div>
      <ServiceProgress reservation={r} />
      <div className="row">
        {canProvider && providerStatusActions(r).map((s) => <button key={s} className={s === "rechazado" ? "warning" : ""} onClick={() => run(() => api(`/api/reservations/${r.id}/status/`, { method: "POST", body: { status: s } }))}>{actionLabel(s)}</button>)}
        {canPay && <button className="secondary" onClick={() => setPaying(!paying)}>{paying ? "Ocultar pago" : "Pagar"}</button>}
      </div>
      {paying && <PaymentGateway reservation={r} run={run} />}
    </article>
  );
}

function ServiceProgress({ reservation }) {
  return (
    <div className="service-progress">
      {serviceSteps(reservation).map((step) => <span key={step.key} className={step.done ? "done" : ""}>{step.label}</span>)}
    </div>
  );
}

function PaymentGateway({ reservation, run }) {
  const [form, setForm] = useState({ card_name: "", card_number: "", expires: "", cvv: "", method_label: "Pasarela demo" });
  const submit = (e) => {
    e.preventDefault();
    run(() => api("/api/payments/", { method: "POST", body: { ...form, reservation_id: reservation.id } }));
  };
  return (
    <form className="payment-gateway grid two" onSubmit={submit}>
      <div className="gateway-head">
        <b>Pasarela de pago demo</b>
        <span className="muted">{money(reservation.total)}</span>
      </div>
      <Field label="Nombre en la tarjeta" value={form.card_name} onChange={(v) => setForm({ ...form, card_name: v })} />
      <Field label="Numero de tarjeta" value={form.card_number} onChange={(v) => setForm({ ...form, card_number: v })} />
      <Field label="Vencimiento" value={form.expires} onChange={(v) => setForm({ ...form, expires: v })} />
      <Field label="CVV" value={form.cvv} onChange={(v) => setForm({ ...form, cvv: v })} />
      <button>Simular pago</button>
    </form>
  );
}

function HistoryCard({ r, profile, run }) {
  const receivedRatings = r.ratings?.filter((rating) => rating.to_profile_id === profile.id) || [];
  const givenRating = r.ratings?.find((rating) => rating.from_profile_id === profile.id);
  const canRate = r.status === "finalizado" && r.is_paid && !givenRating && [r.client.id, r.provider.id].includes(profile.id);
  return (
    <article className="card">
      <div className="row"><h3>{r.service.name}</h3><span className="pill">{r.workflow_status || (r.is_paid ? "Pagado" : "Sin pago")}</span></div>
      <div className="muted">{prettyDate(r.scheduled_for)} · {money(r.total)}</div>
      <div>Cliente: {r.client.full_name}</div>
      <div>Prestador: {r.provider.full_name}</div>
      <ServiceProgress reservation={r} />
      <div className="rating-list">
        <b>Calificaciones</b>
        {r.ratings?.length ? r.ratings.map((rating) => (
          <p key={rating.id} className="muted">{rating.from_name} califico a {rating.to_name}: {rating.stars}/5 {rating.comment ? `- ${rating.comment}` : ""}</p>
        )) : <p className="muted">Sin calificaciones todavia.</p>}
      </div>
      {receivedRatings.length > 0 && <div className="notice">Tu calificacion recibida: {receivedRatings.map((rating) => `${rating.stars}/5`).join(", ")}</div>}
      {canRate && <RatingForm reservationId={r.id} run={run} />}
      {!r.is_paid && <div className="notice">La calificacion se habilita despues del pago.</div>}
    </article>
  );
}

function RatingForm({ reservationId, run }) {
  const [rating, setRating] = useState({ stars: 5, comment: "" });
  return (
    <div className="grid two">
      <label>Estrellas<select value={rating.stars} onChange={(e) => setRating({ ...rating, stars: e.target.value })}>{[5,4,3,2,1].map((n) => <option key={n}>{n}</option>)}</select></label>
      <Field label="Comentario" value={rating.comment} onChange={(v) => setRating({ ...rating, comment: v })} />
      <button className="secondary" onClick={() => run(() => api("/api/ratings/", { method: "POST", body: { ...rating, reservation_id: reservationId } }))}>Calificar</button>
    </div>
  );
}

function Offers({ profile, data, run, setTab }) {
  const [form, setForm] = useState({ title: "", service_type: "oficios", description: "", address: profile.address || "", budget: "", scheduled_for: "" });
  return (
    <section className="section">
      <div className="section-head"><h2>Ofertas</h2><span className="pill">{data.offers.length} registros</span></div>
      {profile.role === "cliente" && (
        <form className="card grid two" onSubmit={(e) => { e.preventDefault(); run(() => api("/api/offers/", { method: "POST", body: form })); }}>
          <Field label="Titulo" value={form.title} onChange={(v) => setForm({ ...form, title: v })} />
          <label>Tipo<select value={form.service_type} onChange={(e) => setForm({ ...form, service_type: e.target.value })}><option value="oficios">Oficios varios</option><option value="lavanderia">Lavanderia</option></select></label>
          <Field label="Presupuesto" type="number" value={form.budget} onChange={(v) => setForm({ ...form, budget: v })} />
          <Field label="Fecha" type="datetime-local" value={form.scheduled_for} onChange={(v) => setForm({ ...form, scheduled_for: v })} />
          <Field label="Direccion" value={form.address} onChange={(v) => setForm({ ...form, address: v })} />
          <label>Descripcion<textarea required value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} /></label>
          <button>Publicar oferta</button>
        </form>
      )}
      <div className="cards">
        {data.offers.map((o) => <OfferCard key={o.id} offer={o} profile={profile} run={run} setTab={setTab} />)}
      </div>
    </section>
  );
}

function OfferCard({ offer, profile, run, setTab }) {
  const [app, setApp] = useState({ message: "", proposed_price: offer.budget });
  const [editing, setEditing] = useState(false);
  const [profileOpen, setProfileOpen] = useState(null);
  const [editForm, setEditForm] = useState({
    title: offer.title,
    service_type: offer.service_type,
    description: offer.description,
    address: offer.address,
    budget: offer.budget,
    scheduled_for: datetimeLocal(offer.scheduled_for),
  });
  const isOwner = profile.role === "cliente" && offer.client?.id === profile.id;
  const hasApplications = (offer.application_count || offer.applications?.length || 0) > 0;
  const canEdit = isOwner && offer.status === "abierta" && !hasApplications;
  const canDelete = isOwner && offer.status === "abierta";
  const saveEdit = (e) => {
    e.preventDefault();
    run(async () => {
      await api(`/api/offers/${offer.id}/`, { method: "PATCH", body: editForm });
      setEditing(false);
    });
  };
  const deleteOffer = () => {
    if (!confirm("Esta oferta se retirara y ya no aparecera publicada. ¿Quieres continuar?")) return;
    run(() => api(`/api/offers/${offer.id}/`, { method: "DELETE" }));
  };
  const acceptApplication = (applicationId) => {
    run(async () => {
      await api(`/api/offers/${offer.id}/choose/${applicationId}/`, { method: "POST" });
      setTab("agenda");
    });
  };
  return (
    <article className="card">
      <div className="row"><h3>{offer.title}</h3><span className="pill">{offer.status}</span></div>
      <div className="muted">{offer.service_type} · {money(offer.budget)} · {prettyDate(offer.scheduled_for)}</div>
      <p>{offer.description}</p>
      <div>{offer.address}</div>
      {(canEdit || canDelete) && !editing && (
        <div className="row">
          {canEdit && <button className="secondary" onClick={() => setEditing(true)}>Editar oferta</button>}
          {canDelete && <button className="warning" onClick={deleteOffer}>Eliminar oferta</button>}
        </div>
      )}
      {isOwner && !canEdit && hasApplications && <div className="notice">Esta oferta ya tiene postulaciones, por eso no se puede editar. Si lo necesitas, puedes eliminarla.</div>}
      {editing && (
        <form className="grid two edit-offer" onSubmit={saveEdit}>
          <Field label="Titulo" value={editForm.title} onChange={(v) => setEditForm({ ...editForm, title: v })} />
          <label>Tipo<select value={editForm.service_type} onChange={(e) => setEditForm({ ...editForm, service_type: e.target.value })}><option value="oficios">Oficios varios</option><option value="lavanderia">Lavanderia</option></select></label>
          <Field label="Presupuesto" type="number" value={editForm.budget} onChange={(v) => setEditForm({ ...editForm, budget: v })} />
          <Field label="Fecha" type="datetime-local" value={editForm.scheduled_for} onChange={(v) => setEditForm({ ...editForm, scheduled_for: v })} />
          <Field label="Direccion" value={editForm.address} onChange={(v) => setEditForm({ ...editForm, address: v })} />
          <label>Descripcion<textarea required value={editForm.description} onChange={(e) => setEditForm({ ...editForm, description: e.target.value })} /></label>
          <div className="row">
            <button>Guardar cambios</button>
            <button type="button" className="secondary" onClick={() => setEditing(false)}>Cancelar</button>
          </div>
        </form>
      )}
      {profile.role !== "cliente" && profile.role !== "admin" && (
        <div className="grid">
          <Field label="Precio propuesto" type="number" value={app.proposed_price} onChange={(v) => setApp({ ...app, proposed_price: v })} />
          <Field label="Mensaje" value={app.message} onChange={(v) => setApp({ ...app, message: v })} />
          <button onClick={() => run(() => api(`/api/offers/${offer.id}/apply/`, { method: "POST", body: app }))}>Postularme</button>
        </div>
      )}
      {profile.role === "cliente" && offer.applications?.length > 0 && (
        <div className="card-list">
          <b>Postulaciones</b>
          {offer.applications.map((a) => (
            <div className="application-item" key={a.id}>
              <div className="row">
                <span>{a.provider.full_name} · {money(a.proposed_price)}</span>
                <button className="secondary" onClick={() => setProfileOpen(profileOpen === a.id ? null : a.id)}>Ver perfil</button>
                <button className="secondary" disabled={offer.status !== "abierta"} onClick={() => acceptApplication(a.id)}>{offer.selected_application_id === a.id ? "Aceptado" : "Aceptar"}</button>
              </div>
              {profileOpen === a.id && <ProviderProfile profile={a.provider} message={a.message} />}
            </div>
          ))}
        </div>
      )}
      {profile.role === "admin" && <button className="warning" onClick={() => run(() => api(`/api/offers/${offer.id}/moderate/`, { method: "POST", body: { status: "eliminada", reason: "Contenido retirado por administracion." } }))}>Eliminar oferta</button>}
    </article>
  );
}

function ProviderProfile({ profile, message }) {
  return (
    <div className="profile-preview">
      <div className="row">
        <b>{profile.full_name}</b>
        <span className="pill">{profile.average_rating}/5 · {profile.rating_count} calificaciones</span>
      </div>
      <div className="grid two">
        <p><b>Rol:</b> {profile.role}</p>
        <p><b>Ciudad:</b> {profile.city || "Sin ciudad"}</p>
        <p><b>Barrio:</b> {profile.neighborhood || "Sin barrio"}</p>
        <p><b>Telefono:</b> {profile.phone || "Sin telefono"}</p>
      </div>
      {profile.bio && <p>{profile.bio}</p>}
      {profile.store_address && <p><b>Punto fisico:</b> {profile.store_address}</p>}
      {message && <p className="muted"><b>Mensaje:</b> {message}</p>}
    </div>
  );
}

function ProfileEditor({ profile, data, run }) {
  const [form, setForm] = useState({ first_name: profile.full_name.split(" ")[0] || "", last_name: profile.full_name.split(" ").slice(1).join(" "), phone: profile.phone, city: profile.city, neighborhood: profile.neighborhood, address: profile.address, bio: profile.bio, store_address: profile.store_address, provides_home_service: profile.provides_home_service });
  const [services, setServices] = useState(data.services.filter((s) => s.provider_id === profile.id));
  const addService = () => setServices([...services, { name: "", description: "", price: 0, duration_minutes: 60 }]);
  return (
    <section className="section">
      <h2>Perfil</h2>
      <form className="card grid two" onSubmit={(e) => { e.preventDefault(); run(() => api("/api/profile/", { method: "POST", body: { ...form, services } })); }}>
        {Object.entries({ first_name: "Nombres", last_name: "Apellidos", phone: "Telefono", city: "Ciudad", neighborhood: "Barrio", address: "Direccion", store_address: "Direccion local" }).map(([k, label]) => <Field key={k} label={label} value={form[k] || ""} onChange={(v) => setForm({ ...form, [k]: v })} />)}
        <label>Biografia<textarea value={form.bio || ""} onChange={(e) => setForm({ ...form, bio: e.target.value })} /></label>
        <label>Servicio a domicilio<select value={String(form.provides_home_service)} onChange={(e) => setForm({ ...form, provides_home_service: e.target.value === "true" })}><option value="true">Si</option><option value="false">No</option></select></label>
        <button>Guardar perfil</button>
      </form>
      {profile.role !== "cliente" && profile.role !== "admin" && (
        <div className="section">
          <div className="section-head"><h3>Servicios y precios</h3><button className="secondary" onClick={addService}>Agregar</button></div>
          {services.map((s, i) => <div className="card grid three" key={i}><Field label="Nombre" value={s.name} onChange={(v) => setServices(services.map((x, ix) => ix === i ? { ...x, name: v } : x))} /><Field label="Precio" type="number" value={s.price} onChange={(v) => setServices(services.map((x, ix) => ix === i ? { ...x, price: v } : x))} /><Field label="Minutos" type="number" value={s.duration_minutes} onChange={(v) => setServices(services.map((x, ix) => ix === i ? { ...x, duration_minutes: v } : x))} /></div>)}
        </div>
      )}
    </section>
  );
}

function Messages({ run }) {
  const [data, setData] = useState({ conversations: [] });
  const [text, setText] = useState({});
  useEffect(() => { api("/api/messages/").then(setData).catch(() => {}); }, []);
  const send = (id) => run(async () => { await api("/api/messages/", { method: "POST", body: { conversation_id: id, body: text[id] || "" } }); setData(await api("/api/messages/")); });
  return <section className="section"><h2>Mensajeria interna</h2>{data.conversations.map((c) => <article className="card" key={c.id}><b>{c.participants.map((p) => p.full_name).join(" / ")}</b>{c.messages.map((m) => <div key={m.id} className="muted">{prettyDate(m.created_at)} · {m.body}</div>)}<div className="row"><input value={text[c.id] || ""} onChange={(e) => setText({ ...text, [c.id]: e.target.value })} placeholder="Escribe un mensaje" /><button onClick={() => send(c.id)}>Enviar</button></div></article>)}</section>;
}

function Notifications({ data, run }) {
  return <section className="section"><div className="section-head"><h2>Notificaciones</h2><button className="secondary" onClick={() => run(() => api("/api/notifications/", { method: "POST" }))}>Marcar leidas</button></div><div className="cards">{data.notifications.map((n) => <article className="card" key={n.id}><b>{n.title}</b><span className="muted">{prettyDate(n.created_at)}</span><p>{n.body}</p></article>)}</div></section>;
}

function AdminPanel({ run }) {
  const [dash, setDash] = useState(null);
  const [pending, setPending] = useState([]);
  const refresh = async () => { setDash(await api("/api/dashboard/")); setPending((await api("/api/admin/pending-profiles/")).profiles); };
  useEffect(() => { refresh().catch(() => {}); }, []);
  if (!dash) return <div>Cargando panel...</div>;
  return (
    <section className="section">
      <div className="section-head"><h2>Panel administrativo</h2><a href="/api/admin/reports.csv"><button>Exportar CSV</button></a></div>
      <div className="stat-grid"><Stat label="Usuarios" value={dash.users} /><Stat label="Pendientes" value={dash.pending_profiles} /><Stat label="Reservas" value={dash.reservations} /><Stat label="Ingresos" value={money(dash.revenue)} /></div>
      <div className="table"><table><thead><tr><th>Perfil FIFO</th><th>Rol</th><th>Correo</th><th>Accion</th></tr></thead><tbody>{pending.map((p) => <tr key={p.id}><td>{p.full_name}</td><td>{p.role}</td><td>{p.email}</td><td className="row"><button onClick={() => run(async () => { await api(`/api/admin/profiles/${p.id}/review/`, { method: "POST", body: { approved: true } }); await refresh(); })}>Aprobar</button><button className="warning" onClick={() => run(async () => { await api(`/api/admin/profiles/${p.id}/review/`, { method: "POST", body: { approved: false } }); await refresh(); })}>Rechazar</button></td></tr>)}</tbody></table></div>
    </section>
  );
}

function Field({ label, value, onChange, type = "text" }) {
  return <label>{label}<input type={type} value={value} onChange={(e) => onChange(e.target.value)} /></label>;
}

function Stat({ label, value }) {
  return <div className="stat"><b>{value}</b><span className="muted">{label}</span></div>;
}

ReactDOM.createRoot(document.getElementById("root")).render(<App />);
