package ke.pricecheck.app

import android.app.Activity
import android.os.Bundle
import android.view.Gravity
import android.widget.Button
import android.widget.LinearLayout
import android.widget.TextView
import androidx.core.view.ViewCompat
import androidx.core.view.WindowInsetsCompat
import androidx.core.view.updatePadding

class AboutActivity : Activity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val padding = (resources.displayMetrics.density * 24).toInt()
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(padding, padding, padding, padding)
            gravity = Gravity.TOP
            addView(
                TextView(context).apply {
                    text = getString(R.string.about_title)
                    textSize = 24f
                },
            )
            addView(
                TextView(context).apply {
                    text = getString(R.string.about_description)
                    textSize = 16f
                    setPadding(0, padding / 2, 0, padding)
                },
            )
            addView(
                Button(context).apply {
                    text = getString(R.string.close)
                    setOnClickListener { finish() }
                },
            )
        }
        ViewCompat.setOnApplyWindowInsetsListener(root) { view, insets ->
            val systemBars = insets.getInsets(WindowInsetsCompat.Type.systemBars())
            view.updatePadding(top = padding + systemBars.top, bottom = padding + systemBars.bottom)
            insets
        }
        setContentView(root)
    }
}
