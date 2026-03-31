import { useCallback, useEffect, useState } from "react";
import {
  clearSession,
  createOrder,
  getOrder,
  getStoredToken,
  getStoredUser,
  listUserOrders,
  loginWithPassword,
  patchOrderStatus,
  registerUser,
  saveSession,
} from "./api";
import type { Order, OrderItem, SessionUser } from "./types";
import { ORDER_STATUSES } from "./types";

const emptyItem = (): OrderItem => ({
  sku: "",
  name: "",
  qty: 1,
  price: 0,
});

export default function App() {
  const [token, setToken] = useState<string | null>(() => getStoredToken());
  const [user, setUser] = useState<SessionUser | null>(() => getStoredUser());

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [authMsg, setAuthMsg] = useState("");

  const [items, setItems] = useState<OrderItem[]>([
    { sku: "demo-sku", name: "Демо-товар", qty: 1, price: 99.99 },
  ]);
  const [createMsg, setCreateMsg] = useState("");

  const [orders, setOrders] = useState<Order[]>([]);
  const [listMsg, setListMsg] = useState("");

  const [orderIdInput, setOrderIdInput] = useState("");
  const [orderDetail, setOrderDetail] = useState<Order | null>(null);
  const [getMsg, setGetMsg] = useState("");
  const [newStatus, setNewStatus] = useState<string>("PENDING");
  const [patchMsg, setPatchMsg] = useState("");

  const loggedIn = Boolean(token && user && Number.isFinite(user.id));

  const refreshOrders = useCallback(async () => {
    if (!token || user?.id == null) return;
    setListMsg("");
    try {
      const rows = await listUserOrders(token, user.id);
      setOrders(rows);
      setListMsg(`Заказов: ${rows.length}`);
    } catch (e) {
      setListMsg(e instanceof Error ? e.message : "Ошибка");
    }
  }, [token, user?.id]);

  useEffect(() => {
    if (loggedIn) void refreshOrders();
  }, [loggedIn, refreshOrders]);

  function applySession(t: string, u: SessionUser) {
    saveSession(t, u);
    setToken(t);
    setUser(u);
  }

  async function handleRegister() {
    setAuthMsg("");
    try {
      await registerUser(email.trim(), password);
      const { token: t, userId } = await loginWithPassword(
        email.trim(),
        password
      );
      applySession(t, { id: userId, email: email.trim() });
      setAuthMsg("Регистрация и вход выполнены");
      await refreshOrders();
    } catch (e) {
      setAuthMsg(e instanceof Error ? e.message : "Ошибка");
    }
  }

  async function handleLogin() {
    setAuthMsg("");
    try {
      const { token: t, userId } = await loginWithPassword(
        email.trim(),
        password
      );
      applySession(t, { id: userId, email: email.trim() });
      setAuthMsg("Вход выполнен");
      await refreshOrders();
    } catch (e) {
      setAuthMsg(e instanceof Error ? e.message : "Ошибка");
    }
  }

  function handleLogout() {
    clearSession();
    setToken(null);
    setUser(null);
    setOrderDetail(null);
    setOrders([]);
  }

  function updateItem(i: number, patch: Partial<OrderItem>) {
    setItems((prev) =>
      prev.map((row, j) => (j === i ? { ...row, ...patch } : row))
    );
  }

  function addItemRow() {
    setItems((prev) => [...prev, emptyItem()]);
  }

  function removeItemRow(i: number) {
    setItems((prev) => prev.filter((_, j) => j !== i));
  }

  function parseItems(): OrderItem[] {
    if (!items.length) throw new Error("Добавьте хотя бы одну позицию");
    const out: OrderItem[] = [];
    for (const row of items) {
      const sku = row.sku.trim();
      const name = row.name.trim();
      const qty = row.qty;
      const price = row.price;
      if (
        !sku ||
        !name ||
        !Number.isFinite(qty) ||
        qty < 1 ||
        !Number.isFinite(price) ||
        price <= 0
      ) {
        throw new Error("Заполните позиции: qty ≥ 1, price > 0");
      }
      out.push({ sku, name, qty, price });
    }
    return out;
  }

  async function handleCreateOrder() {
    if (!token) return;
    setCreateMsg("");
    try {
      const created = await createOrder(token, parseItems());
      setCreateMsg(`Создан заказ ${created.id}`);
      await refreshOrders();
    } catch (e) {
      setCreateMsg(e instanceof Error ? e.message : "Ошибка");
    }
  }

  async function handleGetOrder() {
    if (!token) return;
    const id = orderIdInput.trim();
    setGetMsg("");
    setOrderDetail(null);
    if (!id) {
      setGetMsg("Укажите UUID");
      return;
    }
    try {
      const o = await getOrder(token, id);
      setOrderDetail(o);
      setNewStatus(o.status);
      setGetMsg("OK");
    } catch (e) {
      setGetMsg(e instanceof Error ? e.message : "Ошибка");
    }
  }

  async function handlePatchStatus() {
    if (!token) return;
    const id = orderIdInput.trim();
    setPatchMsg("");
    if (!id) {
      setPatchMsg("Сначала загрузите заказ");
      return;
    }
    try {
      const o = await patchOrderStatus(token, id, newStatus);
      setOrderDetail(o);
      setPatchMsg(`Статус: ${o.status}`);
      await refreshOrders();
    } catch (e) {
      setPatchMsg(e instanceof Error ? e.message : "Ошибка");
    }
  }

  return (
    <>
      <h1>Order Service</h1>
      <p className="sub">
        Запросы идут на <code>/api</code> (в Docker nginx проксирует на API).
      </p>

      {!loggedIn && (
        <section>
          <h2>Вход и регистрация</h2>
          <div className="row">
            <div>
              <label htmlFor="email">Email</label>
              <input
                id="email"
                className="field"
                type="email"
                autoComplete="username"
                placeholder="user@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </div>
            <div>
              <label htmlFor="password">
                Пароль (≥8 символов, буквы и цифры)
              </label>
              <input
                id="password"
                className="field"
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </div>
          </div>
          <button type="button" onClick={() => void handleLogin()}>
            Войти
          </button>
          <button
            type="button"
            className="secondary"
            onClick={() => void handleRegister()}
          >
            Регистрация
          </button>
          <div
            className={
              !authMsg
                ? "msg"
                : authMsg.includes("выполнен")
                  ? "msg ok"
                  : "msg err"
            }
          >
            {authMsg}
          </div>
        </section>
      )}

      {loggedIn && user && (
        <>
          <section>
            <h2>Сессия</h2>
            <p
              style={{
                margin: "0 0 0.5rem",
                fontSize: "0.9rem",
                color: "var(--muted)",
              }}
            >
              Пользователь id={user.id}, {user.email}
            </p>
            <button type="button" className="secondary" onClick={handleLogout}>
              Выйти
            </button>
          </section>

          <section>
            <h2>Новый заказ</h2>
            <div style={{ marginTop: "0.75rem" }}>
              {items.map((row, i) => (
                <div key={i} className="item-line">
                  <input
                    placeholder="sku"
                    value={row.sku}
                    onChange={(e) => updateItem(i, { sku: e.target.value })}
                  />
                  <input
                    placeholder="название"
                    value={row.name}
                    onChange={(e) => updateItem(i, { name: e.target.value })}
                  />
                  <input
                    type="number"
                    min={1}
                    step={1}
                    value={row.qty}
                    onChange={(e) =>
                      updateItem(i, { qty: parseInt(e.target.value, 10) || 0 })
                    }
                  />
                  <input
                    type="number"
                    min={0.01}
                    step={0.01}
                    placeholder="цена"
                    value={row.price || ""}
                    onChange={(e) =>
                      updateItem(i, {
                        price: parseFloat(e.target.value) || 0,
                      })
                    }
                  />
                  <button
                    type="button"
                    className="secondary"
                    onClick={() => removeItemRow(i)}
                  >
                    ✕
                  </button>
                </div>
              ))}
            </div>
            <button type="button" className="secondary" onClick={addItemRow}>
              + позиция
            </button>
            <button type="button" onClick={() => void handleCreateOrder()}>
              Создать заказ
            </button>
            <div
              className={
                !createMsg
                  ? "msg"
                  : createMsg.startsWith("Создан")
                    ? "msg ok"
                    : "msg err"
              }
            >
              {createMsg}
            </div>
          </section>

          <section>
            <h2>Мои заказы</h2>
            <button type="button" onClick={() => void refreshOrders()}>
              Обновить список
            </button>
            <div
              className={
                !listMsg
                  ? "msg"
                  : listMsg.startsWith("Заказов:")
                    ? "msg ok"
                    : "msg err"
              }
            >
              {listMsg}
            </div>
            <table>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Статус</th>
                  <th>Сумма</th>
                  <th>Создан</th>
                </tr>
              </thead>
              <tbody>
                {orders.map((o) => (
                  <tr
                    key={o.id}
                    style={{ cursor: "pointer" }}
                    title="Подставить ID в поле ниже"
                    onClick={() => setOrderIdInput(o.id)}
                  >
                    <td>{o.id}</td>
                    <td>{o.status}</td>
                    <td>{o.total_price}</td>
                    <td>{o.created_at}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>

          <section>
            <h2>Заказ по ID</h2>
            <div className="row">
              <div>
                <label htmlFor="order-id">UUID заказа</label>
                <input
                  id="order-id"
                  className="field"
                  placeholder="вставьте из таблицы"
                  value={orderIdInput}
                  onChange={(e) => setOrderIdInput(e.target.value)}
                />
              </div>
            </div>
            <button type="button" onClick={() => void handleGetOrder()}>
              Загрузить
            </button>
            <div
              className={
                !getMsg ? "msg" : getMsg === "OK" ? "msg ok" : "msg err"
              }
            >
              {getMsg}
            </div>
            {orderDetail && (
              <pre>{JSON.stringify(orderDetail, null, 2)}</pre>
            )}

            {orderDetail && (
              <>
                <h2 style={{ marginTop: "1rem" }}>Сменить статус</h2>
                <div className="row">
                  <div>
                    <label htmlFor="new-status">Статус</label>
                    <select
                      id="new-status"
                      className="field"
                      value={newStatus}
                      onChange={(e) => setNewStatus(e.target.value)}
                    >
                      {ORDER_STATUSES.map((s) => (
                        <option key={s} value={s}>
                          {s}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
                <button type="button" onClick={() => void handlePatchStatus()}>
                  PATCH статус
                </button>
                <div
                  className={
                    !patchMsg
                      ? "msg"
                      : patchMsg.startsWith("Статус:")
                        ? "msg ok"
                        : "msg err"
                  }
                >
                  {patchMsg}
                </div>
              </>
            )}
          </section>
        </>
      )}
    </>
  );
}
