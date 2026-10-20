import { FoodInflationResponse } from '../types/market';

const MONTHS: Record<string, string> = {
  january: 'Jan',
  jan: 'Jan',
  february: 'Feb',
  feb: 'Feb',
  march: 'Mar',
  mar: 'Mar',
  april: 'Apr',
  apr: 'Apr',
  may: 'May',
  june: 'Jun',
  jun: 'Jun',
  july: 'Jul',
  jul: 'Jul',
  august: 'Aug',
  aug: 'Aug',
  september: 'Sep',
  sep: 'Sep',
  october: 'Oct',
  oct: 'Oct',
  november: 'Nov',
  nov: 'Nov',
  december: 'Dec',
  dec: 'Dec',
};

function formatValue(value: number): string {
  return `${value.toFixed(2)}%`;
}

export function answerMarketQuestionFromData(
  question: string,
  data: FoodInflationResponse,
): string {
  const normalized = question.toLowerCase();
  const { observations, summary } = data;

  if (/\b(why|cause|caused|reason)\b/.test(normalized)) {
    return (
      'This dataset shows how the national food-price inflation index changed over time, ' +
      'but it does not identify why it changed or prove a cause.'
    );
  }

  if (/\b(forecast|predict|prediction|future)\b/.test(normalized)) {
    return (
      'This is historical data, not a forecast. It cannot tell us what food prices will be ' +
      'in the future.'
    );
  }

  if (/\b(supermarket|store|shop|brand|product|retailer)\b/.test(normalized)) {
    return (
      'This national index does not contain verified product or supermarket prices. ' +
      'The app’s store-price examples are illustrative demo data.'
    );
  }

  const requestedMonth = Object.entries(MONTHS).find(([name]) =>
    new RegExp(`\\b${name}\\b`).test(normalized),
  )?.[1];
  const requestedYear = normalized.match(/\b(19|20)\d{2}\b/);

  if (requestedMonth && requestedYear) {
    const observation = observations.find(
      (item) =>
        item.month === requestedMonth && item.year === Number(requestedYear[0]),
    );
    if (observation) {
      return (
        `The reported national food-price inflation index for ${observation.month} ` +
        `${observation.year} was ${formatValue(observation.value)}. This is an index ` +
        'reading, not the price of a food item.'
      );
    }
    return `There is no reported observation for ${requestedMonth} ${requestedYear[0]} in this dataset.`;
  }

  if (requestedYear) {
    const year = Number(requestedYear[0]);
    const yearObservations = observations.filter((item) => item.year === year);
    if (yearObservations.length > 0) {
      const mean =
        yearObservations.reduce((total, item) => total + item.value, 0) /
        yearObservations.length;
      const highest = yearObservations.reduce((best, item) =>
        item.value > best.value ? item : best,
      );
      const lowest = yearObservations.reduce((best, item) =>
        item.value < best.value ? item : best,
      );
      return (
        `For ${year}, the dataset has ${yearObservations.length} reported monthly values. ` +
        `Their mean was ${formatValue(mean)}; the highest was ${formatValue(highest.value)} ` +
        `in ${highest.month}, and the lowest was ${formatValue(lowest.value)} in ` +
        `${lowest.month}. These describe the historical national index.`
      );
    }
    return `There are no reported observations for ${year} in this dataset.`;
  }

  if (/\b(latest|most recent|current|last month)\b/.test(normalized)) {
    const change = summary.change_from_previous;
    const direction = change > 0 ? 'up' : change < 0 ? 'down' : 'unchanged';
    return (
      `The latest reported observation is ${formatValue(summary.latest_value)} for ` +
      `${summary.latest_month}. That is ${direction} ${Math.abs(change).toFixed(2)} ` +
      `percentage points from ${summary.previous_month}. This is a national food-price index reading, ` +
      'not a supermarket price.'
    );
  }

  if (/\b(mean|average|overall)\b/.test(normalized)) {
    return (
      `Across ${summary.observation_count} reported monthly observations from ` +
      `${data.series.coverage_start} to ${data.series.coverage_end}, the mean was ` +
      `${formatValue(summary.mean_value)}. This is the historical national index average, ` +
      'not an average price paid by shoppers.'
    );
  }

  if (/\b(highest|maximum|peak|largest)\b/.test(normalized)) {
    return (
      `The highest reported value was ${formatValue(summary.peak_value)} in ` +
      `${summary.peak_month}. This is the peak of the historical national index series.`
    );
  }

  if (/\b(lowest|minimum|smallest)\b/.test(normalized)) {
    return (
      `The lowest reported value was ${formatValue(summary.minimum_value)} in ` +
      `${summary.minimum_month}. This is the lowest value in the historical national index series.`
    );
  }

  return (
    `The dataset contains ${summary.observation_count} reported monthly observations from ` +
    `${data.series.coverage_start} to ${data.series.coverage_end}. The latest is ` +
    `${formatValue(summary.latest_value)} for ${summary.latest_month}; the mean is ` +
    `${formatValue(summary.mean_value)}. This is historical national index data, not a ` +
    'supermarket price or a forecast.'
  );
}
