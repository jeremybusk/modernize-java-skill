package example;

import java.util.Map;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Bean;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

@SpringBootApplication
public class Application {
    public static void main(String[] args) { SpringApplication.run(Application.class, args); }
    @Bean GreetingService greetingService() { return new GreetingService(); }
    public static class GreetingService { public String greeting() { return "hello"; } }
    @RestController
    public static class GreetingController {
        private final GreetingService service;
        public GreetingController(GreetingService service) { this.service = service; }
        @GetMapping("/hello") public Map<String, String> hello() { return Map.of("message", service.greeting()); }
    }
}
