package ke.pricecheck.app.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.ui.unit.dp
import ke.pricecheck.app.R
import ke.pricecheck.app.ui.PriceCheckUiState
import ke.pricecheck.app.ui.components.SectionTitle

@Composable
fun ProfileScreen(
    state: PriceCheckUiState,
    onBudgetInput: (String) -> Unit,
    onSaveBudget: () -> Unit,
) {
    LazyColumn(
        contentPadding = androidx.compose.foundation.layout.PaddingValues(16.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp),
    ) {
        item {
            SectionTitle(
                stringResource(R.string.profile_settings),
                stringResource(R.string.profile_local_preferences),
            )
        }
        item {
            Card {
                Column(
                    modifier = Modifier.padding(16.dp),
                    verticalArrangement = Arrangement.spacedBy(10.dp),
                ) {
                    Text(stringResource(R.string.weekly_budget))
                    OutlinedTextField(
                        value = state.budgetInput ?: state.preferences.weeklyBudget.toString(),
                        onValueChange = onBudgetInput,
                        modifier = Modifier.fillMaxWidth(),
                        label = { Text(stringResource(R.string.budget_ksh)) },
                        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                        singleLine = true,
                    )
                    Button(onClick = onSaveBudget) { Text(stringResource(R.string.save_budget)) }
                    if (state.budgetError != null) {
                        Text(
                            stringResource(state.budgetError),
                            color = MaterialTheme.colorScheme.error,
                        )
                    }
                }
            }
        }
    }
}
