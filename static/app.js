// Generated with AI, reviewed and modified by the team
// static/app.js - Full Real-Time Live Status & Cross-Role Synchronization

// Status color class map as defined in the project contract
const STATUS_COLORS = {
  posted: "bg-gray-100 text-gray-800",
  matched: "bg-blue-100 text-blue-800",
  accepted: "bg-yellow-100 text-yellow-800",
  assigned: "bg-purple-100 text-purple-800",
  picked_up: "bg-orange-100 text-orange-800",
  delivered: "bg-green-100 text-green-800",
  declined: "bg-red-100 text-red-800",
  expired: "bg-red-100 text-red-800",
  cancelled: "bg-red-100 text-red-800"
};

// All color classes so we can safely remove them before applying new ones
const ALL_COLOR_CLASSES = [
  "bg-gray-100", "text-gray-800", "bg-blue-100", "text-blue-800",
  "bg-yellow-100", "text-yellow-800", "bg-purple-100", "text-purple-800",
  "bg-orange-100", "text-orange-800", "bg-green-100", "text-green-800",
  "bg-red-100", "text-red-800"
];

// Track state snapshots so we only re-render DOM when data actually changes
let lastNgoOffersJson = "";
let lastVolunteerTasksJson = "";

// -----------------------------------------------------------------------------
// 1. DONOR PAGE: Poll active donation badges, assigned NGO name, & live OTP code
// -----------------------------------------------------------------------------
function pollDonationStatuses() {
  const badges = document.querySelectorAll('[id^="status-"]');
  if (badges.length === 0) return;

  badges.forEach((badge) => {
    const donationId = badge.id.replace("status-", "");
    if (!donationId) return;

    fetch(`/api/status/${donationId}`)
      .then((res) => {
        if (!res.ok) throw new Error("API error");
        return res.json();
      })
      .then((data) => {
        if (!data || !data.status) return;

        // 1. Update status badge text & styling
        badge.textContent = data.status;
        badge.classList.remove(...ALL_COLOR_CLASSES);
        const newClasses = (STATUS_COLORS[data.status] || STATUS_COLORS.posted).split(" ");
        badge.classList.add(...newClasses);

        // 2. Update NGO name if element exists
        const ngoSpan = document.getElementById(`ngo-name-${data.id}`);
        if (ngoSpan && data.ngo_name) {
          ngoSpan.textContent = data.ngo_name;
        }

        // 3. Update Volunteer name if element exists
        const volSpan = document.getElementById(`volunteer-name-${data.id}`);
        if (volSpan && data.volunteer_name) {
          volSpan.textContent = data.volunteer_name;
        }

        // 4. Update OTP live in real time when NGO accepts!
        const otpSpan = document.getElementById(`otp-${data.id}`);
        if (otpSpan && data.otp) {
          if (otpSpan.textContent.trim() !== data.otp) {
            otpSpan.textContent = data.otp;
            otpSpan.className = "font-mono font-extrabold text-green-700 bg-green-100 px-1.5 py-0.5 rounded";
          }
        }
      })
      .catch(() => {});
  });
}

// -----------------------------------------------------------------------------
// 2. NGO OFFERS PAGE: Auto-sync new food donations in real time
// -----------------------------------------------------------------------------
function pollNgoOffers() {
  const container = document.getElementById("ngo-offers-container");
  if (!container) return;

  fetch("/api/ngo/offers")
    .then((res) => {
      if (!res.ok) throw new Error("API error");
      return res.json();
    })
    .then((offers) => {
      if (!Array.isArray(offers)) return;

      const currentJson = JSON.stringify(offers);
      if (currentJson === lastNgoOffersJson) return;
      lastNgoOffersJson = currentJson;

      if (offers.length === 0) {
        container.innerHTML = `
          <div class="p-6 bg-white rounded-lg border border-gray-200 text-center text-sm text-gray-500">
            <span class="text-2xl block mb-1">✨</span>
            <p class="font-semibold text-gray-700">No pending food offers right now.</p>
            <p class="text-xs text-gray-400 mt-1">New donations posted by nearby hostels & restaurants will appear here automatically in real time!</p>
          </div>`;
        return;
      }

      container.innerHTML = offers
        .map(
          (offer) => `
        <div id="offer-card-${offer.id}" class="bg-white rounded-lg shadow border border-gray-200 p-4 space-y-3">
          <div class="flex justify-between items-start">
            <div>
              <h3 class="font-bold text-base text-gray-800">${offer.food_type}</h3>
              <p class="text-xs text-gray-500">Donor: <span class="font-medium text-gray-700">${offer.donor_name}</span></p>
            </div>
            <span class="text-xs font-semibold bg-green-100 text-green-800 px-2 py-0.5 rounded">
              ${offer.distance_km} km away
            </span>
          </div>

          <div class="grid grid-cols-2 gap-2 text-xs bg-gray-50 p-2.5 rounded border border-gray-100">
            <div>
              <span class="text-gray-500 block">Quantity:</span>
              <span class="font-bold text-gray-800 text-sm">${offer.quantity_kg} kg</span>
            </div>
            <div>
              <span class="text-gray-500 block">Safe Until:</span>
              <span class="font-bold text-red-600">${offer.safe_until}</span>
            </div>
          </div>

          <div class="flex items-center gap-3 pt-1">
            <form action="/accept/${offer.id}" method="POST" class="flex-1">
              <button type="submit"
                class="w-full bg-green-600 hover:bg-green-700 text-white font-semibold px-4 py-2 rounded text-sm transition shadow-sm">
                Accept Offer
              </button>
            </form>
            <form action="/decline/${offer.id}" method="POST" class="flex-1">
              <button type="submit"
                class="w-full bg-red-600 hover:bg-red-700 text-white font-semibold px-4 py-2 rounded text-sm transition shadow-sm">
                Decline
              </button>
            </form>
          </div>
        </div>
      `
        )
        .join("");
    })
    .catch(() => {});
}

// -----------------------------------------------------------------------------
// 3. VOLUNTEER TASKS PAGE: Auto-sync accepted missions & pickup handoffs
// -----------------------------------------------------------------------------
function pollVolunteerTasks() {
  const container = document.getElementById("volunteer-tasks-container");
  if (!container) return;

  fetch("/api/volunteer/tasks")
    .then((res) => {
      if (!res.ok) throw new Error("API error");
      return res.json();
    })
    .then((tasks) => {
      if (!Array.isArray(tasks)) return;

      const currentJson = JSON.stringify(tasks);
      if (currentJson === lastVolunteerTasksJson) return;
      lastVolunteerTasksJson = currentJson;

      if (tasks.length === 0) {
        container.innerHTML = `
          <div class="p-6 bg-white rounded-lg border border-gray-200 text-center text-sm text-gray-500">
            <span class="text-2xl block mb-1">🛵</span>
            <p class="font-semibold text-gray-700">No active delivery tasks.</p>
            <p class="text-xs text-gray-400 mt-1">When an NGO accepts a donation, the task will appear here live with the OTP pickup form!</p>
          </div>`;
        return;
      }

      container.innerHTML = tasks
        .map((t) => {
          let statusBadgeClass = "bg-gray-100 text-gray-800";
          if (t.status === "assigned") statusBadgeClass = "bg-purple-100 text-purple-800";
          else if (t.status === "picked_up") statusBadgeClass = "bg-orange-100 text-orange-800";
          else if (t.status === "delivered") statusBadgeClass = "bg-green-100 text-green-800";

          let actionFormHtml = "";
          if (t.status === "assigned") {
            actionFormHtml = `
              <form action="/pickup/${t.id}" method="POST" class="pt-2">
                <label class="block text-xs font-semibold text-gray-700 mb-1">
                  Enter 4-Digit Donor Verification OTP:
                </label>
                <div class="flex gap-2">
                  <input type="text" name="otp" required maxlength="4" pattern="[0-9]{4}" placeholder="e.g. 4821"
                    class="flex-1 px-3 py-2 border border-gray-300 rounded text-center tracking-widest font-mono text-base font-bold focus:ring-2 focus:ring-purple-500 focus:outline-none bg-white">
                  <button type="submit"
                    class="bg-purple-600 hover:bg-purple-700 text-white font-semibold px-4 py-2 rounded text-sm transition shadow-sm">
                    Confirm Pickup
                  </button>
                </div>
              </form>`;
          } else if (t.status === "picked_up") {
            actionFormHtml = `
              <form action="/deliver/${t.id}" method="POST" class="pt-2">
                <button type="submit"
                  class="w-full bg-green-600 hover:bg-green-700 text-white font-semibold py-2.5 px-4 rounded text-sm transition shadow-sm">
                  ✓ Mark As Delivered
                </button>
              </form>`;
          }

          return `
            <div class="bg-white rounded-lg shadow border border-gray-200 p-4 space-y-3">
              <div class="flex justify-between items-start">
                <div>
                  <h3 class="font-bold text-gray-800 text-base">${t.food_type}</h3>
                  <p class="text-xs text-gray-500">Weight: <span class="font-semibold text-gray-700">${t.quantity_kg} kg</span></p>
                </div>
                <span id="status-${t.id}" class="px-2.5 py-1 rounded-full text-xs font-semibold uppercase ${statusBadgeClass}">
                  ${t.status}
                </span>
              </div>

              <div class="text-xs space-y-1.5 bg-gray-50 p-3 rounded border border-gray-100">
                <div><span class="text-gray-400 font-medium">Pickup At:</span> <span class="font-semibold text-gray-700">${t.pickup_address}</span></div>
                <div><span class="text-gray-400 font-medium">Deliver To:</span> <span class="font-semibold text-gray-700">${t.ngo_name}</span></div>
                <div><span class="text-gray-400 font-medium">Safe Until:</span> <span class="font-bold text-red-600">${t.safe_until}</span></div>
              </div>

              ${actionFormHtml}
            </div>`;
        })
        .join("");
    })
    .catch(() => {});
}

// -----------------------------------------------------------------------------
// 4. MASTER POLLER: Executes every 5 seconds (5000 ms) as specified in contract
// -----------------------------------------------------------------------------
function runMasterPolling() {
  pollDonationStatuses();
  pollNgoOffers();
  pollVolunteerTasks();
}

document.addEventListener("DOMContentLoaded", () => {
  // Run once immediately on load, then every 5 seconds
  runMasterPolling();
  setInterval(runMasterPolling, 5000);
});
