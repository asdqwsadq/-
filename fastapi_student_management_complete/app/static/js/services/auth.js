const tokenKey = "app_token";
const roleKey = "app_role";
const usernameKey = "app_username";

export function getToken() {
  return localStorage.getItem(tokenKey);
}

export function setToken(token) {
  localStorage.setItem(tokenKey, token);
}

export function clearToken() {
  localStorage.removeItem(tokenKey);
  localStorage.removeItem(roleKey);
  localStorage.removeItem(usernameKey);
}

export function getRole() {
  return localStorage.getItem(roleKey) || "";
}

export function setUserAuth({ role, username }) {
  localStorage.setItem(roleKey, role);
  localStorage.setItem(usernameKey, username);
}

export function isAdmin() {
  return getRole() === "admin";
}

export function canWrite() {
  const role = getRole();
  return role === "teacher" || role === "admin";
}
