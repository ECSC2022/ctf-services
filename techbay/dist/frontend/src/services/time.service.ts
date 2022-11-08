export function dateToDifferenceString(timestamp: Date): string {
  const currentDate = new Date();
  const diff = (currentDate.getTime() - timestamp.getTime()) / 1000;
  if (diff < 60) {
    return `${diff.toFixed(0)} s ago`;
  } else if (diff < 60 * 60) {
    return `${(diff / 60).toFixed(0)} m ago`;
  } else if (diff < 60 * 60 * 60) {
    return `${(diff / 60 / 60).toFixed(0)} h ago`;
  } else if (diff < 60 * 60 * 60 * 24) {
    return `${(diff / 60 / 60 / 60).toFixed(0)} d ago`;
  }
  return `long ago`;
}
