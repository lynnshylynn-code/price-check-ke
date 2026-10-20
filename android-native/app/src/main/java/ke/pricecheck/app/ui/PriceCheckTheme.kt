package ke.pricecheck.app.ui

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

private val LightPriceCheckColors = lightColorScheme(
    primary = Color(0xFF07583E),
    onPrimary = Color.White,
    secondary = Color(0xFF4D755C),
    background = Color(0xFFF6F8F5),
    surface = Color.White,
    error = Color(0xFFB5472A),
)

private val DarkPriceCheckColors = darkColorScheme(
    primary = Color(0xFF8BD4AE),
    onPrimary = Color(0xFF003824),
    secondary = Color(0xFFB1D4B9),
    background = Color(0xFF101512),
    surface = Color(0xFF191F1B),
    error = Color(0xFFFFB4A0),
)

private val PriceCheckTypography = androidx.compose.material3.Typography(
    headlineMedium = TextStyle(fontSize = 28.sp, fontWeight = FontWeight.Bold, lineHeight = 34.sp),
    titleLarge = TextStyle(fontSize = 22.sp, fontWeight = FontWeight.SemiBold, lineHeight = 28.sp),
    titleMedium = TextStyle(fontSize = 17.sp, fontWeight = FontWeight.SemiBold, lineHeight = 23.sp),
)

private val PriceCheckShapes = androidx.compose.material3.Shapes(
    extraSmall = RoundedCornerShape(8.dp),
    small = RoundedCornerShape(12.dp),
    medium = RoundedCornerShape(18.dp),
    large = RoundedCornerShape(24.dp),
    extraLarge = RoundedCornerShape(32.dp),
)

@Composable
fun PriceCheckTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = if (isSystemInDarkTheme()) DarkPriceCheckColors else LightPriceCheckColors,
        typography = PriceCheckTypography,
        shapes = PriceCheckShapes,
        content = content,
    )
}
