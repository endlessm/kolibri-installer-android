package org.endlessos.key;

import static org.junit.Assert.assertEquals;

import androidx.lifecycle.Lifecycle.State;
import androidx.test.core.app.ActivityScenario;

import org.junit.Test;

public class KolibriActivityTest {
    private static final String TAG = "KolibriActivityTest";

    @Test
    public void testLaunch() {
        try (ActivityScenario<KolibriActivity> scenario =
                ActivityScenario.launch(KolibriActivity.class)) {
            assertEquals(State.RESUMED, scenario.getState());
        }
    }

    @Test
    public void testStates() {
        try (ActivityScenario<KolibriActivity> scenario =
                ActivityScenario.launch(KolibriActivity.class)) {
            Logger.i("Moving to RESUMED, current state is " + scenario.getState());
            scenario.moveToState(State.RESUMED);
            Logger.i("Moving to STARTED, current state is " + scenario.getState());
            scenario.moveToState(State.STARTED);
            Logger.i("Moving to CREATED, current state is " + scenario.getState());
            scenario.moveToState(State.CREATED);
            Logger.i("Moving to DESTROYED, current state is " + scenario.getState());
            scenario.moveToState(State.DESTROYED);
        }
    }
}
