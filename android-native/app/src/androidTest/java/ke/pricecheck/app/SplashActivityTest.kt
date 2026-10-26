package ke.pricecheck.app

import androidx.test.core.app.ActivityScenario
import androidx.test.espresso.intent.Intents
import androidx.test.espresso.intent.matcher.IntentMatchers.hasComponent
import androidx.test.ext.junit.runners.AndroidJUnit4
import org.junit.Test
import org.junit.runner.RunWith
import java.util.concurrent.TimeUnit

@RunWith(AndroidJUnit4::class)
class SplashActivityTest {
    @Test
    fun launchingSplashActivityEventuallyShowsMainActivity() {
        Intents.init()
        try {
            ActivityScenario.launch(SplashActivity::class.java).use { scenario ->
                scenario.onActivity { activity ->
                    val deadline = System.currentTimeMillis() + TimeUnit.SECONDS.toMillis(5)
                    while (System.currentTimeMillis() < deadline) {
                        if (activity.isFinishing || activity.isDestroyed) {
                            break
                        }
                        Thread.sleep(100)
                    }
                }
            }
            Intents.intended(hasComponent(MainActivity::class.java.name))
        } finally {
            Intents.release()
        }
    }
}
