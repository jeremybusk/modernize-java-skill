package example;

import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.assertEquals;

class MainTest {
    @Test void preservesStartupContract() { assertEquals("MIGRATION_OK", Main.message()); }
}
