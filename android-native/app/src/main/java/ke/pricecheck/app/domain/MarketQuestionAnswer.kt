package ke.pricecheck.app.domain

import ke.pricecheck.app.data.FoodInflationData

private val monthNames = mapOf(
    "january" to "Jan", "jan" to "Jan",
    "february" to "Feb", "feb" to "Feb",
    "march" to "Mar", "mar" to "Mar",
    "april" to "Apr", "apr" to "Apr",
    "may" to "May",
    "june" to "Jun", "jun" to "Jun",
    "july" to "Jul", "jul" to "Jul",
    "august" to "Aug", "aug" to "Aug",
    "september" to "Sep", "sep" to "Sep",
    "october" to "Oct", "oct" to "Oct",
    "november" to "Nov", "nov" to "Nov",
    "december" to "Dec", "dec" to "Dec",
)

private fun formatValue(value: Double) = "${"%.2f".format(java.util.Locale.ROOT, value)}%"

fun answerFromDataset(question: String, data: FoodInflationData): String {
    val normalized = question.lowercase()
    val summary = data.summary

    if (Regex("\\b(why|cause|caused|reason)\\b").containsMatchIn(normalized)) {
        return "This dataset shows how the national food-price inflation index changed over time, " +
            "but it does not identify why it changed or prove a cause."
    }
    if (Regex("\\b(forecast|predict|prediction|future)\\b").containsMatchIn(normalized)) {
        return "This is historical data, not a forecast. It cannot tell us what food prices will be in the future."
    }
    if (Regex("\\b(supermarket|store|shop|brand|product|retailer)\\b").containsMatchIn(normalized)) {
        return "This national index does not contain verified product or supermarket prices. " +
            "The app's store-price examples are illustrative demo data."
    }

    val month = monthNames.entries.firstOrNull { (name, _) ->
        Regex("\\b${Regex.escape(name)}\\b").containsMatchIn(normalized)
    }?.value
    val year = Regex("\\b(?:19|20)\\d{2}\\b").find(normalized)?.value?.toIntOrNull()

    if (month != null && year != null) {
        val observation = data.observations.firstOrNull {
            it.month == month && it.year == year
        } ?: return "There is no reported observation for $month $year in this dataset."
        return "The reported national food-price inflation index for ${observation.month} " +
            "${observation.year} was ${formatValue(observation.value)}. This is an index reading, " +
            "not the price of a food item."
    }

    if (year != null) {
        val yearObservations = data.observations.filter { it.year == year }
        if (yearObservations.isEmpty()) {
            return "There are no reported observations for $year in this dataset."
        }
        val mean = yearObservations.map { it.value }.average()
        val highest = yearObservations.maxBy { it.value }
        val lowest = yearObservations.minBy { it.value }
        return "For $year, the dataset has ${yearObservations.size} reported monthly values. " +
            "Their mean was ${formatValue(mean)}; the highest was ${formatValue(highest.value)} " +
            "in ${highest.month}, and the lowest was ${formatValue(lowest.value)} in ${lowest.month}. " +
            "These describe the historical national index."
    }

    if (Regex("\\b(latest|most recent|current|last month)\\b").containsMatchIn(normalized)) {
        val direction = when {
            summary.changeFromPrevious > 0 -> "up"
            summary.changeFromPrevious < 0 -> "down"
            else -> "unchanged"
        }
        return "The latest reported observation is ${formatValue(summary.latestValue)} for " +
            "${summary.latestMonth}. That is $direction " +
            "${"%.2f".format(java.util.Locale.ROOT, kotlin.math.abs(summary.changeFromPrevious))} " +
            "percentage points from ${summary.previousMonth}. This is a national food-price " +
            "index reading, not a supermarket price."
    }

    if (Regex("\\b(mean|average|overall)\\b").containsMatchIn(normalized)) {
        return "Across ${summary.observationCount} reported monthly observations from " +
            "${data.series.coverageStart} to ${data.series.coverageEnd}, the mean was " +
            "${formatValue(summary.meanValue)}. This is the historical national index average, " +
            "not an average price paid by shoppers."
    }

    if (Regex("\\b(highest|maximum|peak|largest)\\b").containsMatchIn(normalized)) {
        return "The highest reported value was ${formatValue(summary.peakValue)} in " +
            "${summary.peakMonth}. This is the peak of the historical national index series."
    }

    if (Regex("\\b(lowest|minimum|smallest)\\b").containsMatchIn(normalized)) {
        return "The lowest reported value was ${formatValue(summary.minimumValue)} in " +
            "${summary.minimumMonth}. This is the lowest value in the historical national index series."
    }

    return "The dataset contains ${summary.observationCount} reported monthly observations from " +
        "${data.series.coverageStart} to ${data.series.coverageEnd}. The latest is " +
        "${formatValue(summary.latestValue)} for ${summary.latestMonth}; the mean is " +
        "${formatValue(summary.meanValue)}. This is historical national index data, not a " +
        "supermarket price or a forecast."
}
