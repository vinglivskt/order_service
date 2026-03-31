export type OrderItem = {
  sku: string;
  name: string;
  qty: number;
  price: number;
};

export type Order = {
  id: string;
  user_id: number;
  items: OrderItem[];
  total_price: number;
  status: string;
  created_at: string;
};

export type SessionUser = {
  id: number;
  email: string;
};

export const ORDER_STATUSES = [
  "PENDING",
  "PAID",
  "SHIPPED",
  "CANCELED",
] as const;
