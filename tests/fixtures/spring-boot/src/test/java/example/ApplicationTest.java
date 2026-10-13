package example;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.mockito.Mockito.when;

@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.NONE)
class ApplicationTest {
    @MockBean Application.GreetingService service;
    @Autowired Application.GreetingController controller;
    @Test void preservesResponseContract() {
        when(service.greeting()).thenReturn("contract");
        assertEquals("contract", controller.hello().get("message"));
    }
}
