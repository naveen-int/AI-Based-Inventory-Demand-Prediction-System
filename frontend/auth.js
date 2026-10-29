
const AUTH_API = "http://127.0.0.1:5000/api/auth";

const authMessage = document.getElementById("authMessage");

function showAuthMessage(message, type = "error") {
  if (!authMessage) return;

  authMessage.textContent = message;
  authMessage.className = `message ${type}`;
}

async function sendAuth(path, payload) {
  const response = await fetch(`${AUTH_API}/${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    credentials: "include",
    body: JSON.stringify(payload)
  });

  const result = await response.json();

  if (!response.ok) {
    throw new Error(result.error || "Request failed.");
  }

  return result;
}

// Login.
const loginForm = document.getElementById("loginForm");

if (loginForm) {
  loginForm.addEventListener("submit", async event => {
    event.preventDefault();

    try {
      await sendAuth("login", {
        email: document.getElementById("email").value,
        password: document.getElementById("password").value
      });

      window.location.href = "index.html";

    } catch (error) {
      showAuthMessage(error.message);
    }
  });
}

// Signup.
const signupForm = document.getElementById("signupForm");

if (signupForm) {
  signupForm.addEventListener("submit", async event => {
    event.preventDefault();

    const password = document.getElementById("password").value;
    const confirmPassword =
      document.getElementById("confirmPassword").value;

    if (password !== confirmPassword) {
      showAuthMessage("Passwords do not match.");
      return;
    }

    try {
      const result = await sendAuth("signup", {
        name: document.getElementById("name").value,
        email: document.getElementById("email").value,
        password,
        confirmPassword
      });

      showAuthMessage(result.message, "success");
      signupForm.reset();

      setTimeout(() => {
        window.location.href = "login.html";
      }, 900);

    } catch (error) {
      showAuthMessage(error.message);
    }
  });
}
