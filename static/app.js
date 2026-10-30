// Generated with AI, reviewed and modified by the team
// static/app.js - Live status polling for Surplus Food Rescue MVP

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

// Polls status for every active donation post on the page
function pollDonationStatuses() {
  // Find all status badges with id starting with "status-"
  const badges = document.querySelectorAll('[id^="status-"]');
  if (badges.length === 0) return;

  badges.forEach((badge) => {
    const donationId = badge.id.replace("status-", "");
    if (!donationId) return;

    // Fetch latest status JSON from backend API
    fetch(`/api/status/${donationId}`)
      .then((res) => {
        if (!res.ok) throw new Error("API error");
        return res.json();
      })
      .then((data) => {
        if (!data || !data.status) return;

        // 1. Update status badge text
        badge.textContent = data.status;

        // 2. Update status badge color
        badge.classList.remove(...ALL_COLOR_CLASSES);
        const newClasses = (STATUS_COLORS[data.status] || STATUS_COLORS.posted).split(" ");
        badge.classList.add(...newClasses);

        // 3. Update NGO and Volunteer names if elements exist
        const ngoSpan = document.getElementById(`ngo-name-${data.id}`);
        if (ngoSpan && data.ngo_name) ngoSpan.textContent = data.ngo_name;

        const volSpan = document.getElementById(`volunteer-name-${data.id}`);
        if (volSpan && data.volunteer_name) volSpan.textContent = data.volunteer_name;
      })
      .catch(() => {
        // Silently ignore network errors so user experience is not disrupted
      });
  });
}

// Start live polling every 5 seconds (5000 ms) as specified in contract
document.addEventListener("DOMContentLoaded", () => {
  setInterval(pollDonationStatuses, 5000);
});
