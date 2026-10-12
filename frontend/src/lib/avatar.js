// Turns a full name into 1-2 uppercase initials for an avatar badge.
// No photo upload exists yet, so every avatar in the app (top bar,
// profile card) is this same initials badge rather than a placeholder
// image that would imply upload support that isn't built.
export function getInitials(fullName) {
  if (!fullName) return "?";
  const parts = fullName.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "?";
  if (parts.length === 1) return parts[0][0].toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}
