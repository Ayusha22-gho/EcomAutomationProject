package ecomautomation.pageObjectClass;

import ecomautomation.AbstarctComponents.AbstractComponent;
import org.openqa.selenium.By;
import org.openqa.selenium.WebDriver;
import org.openqa.selenium.WebElement;
import org.openqa.selenium.support.FindBy;
import org.openqa.selenium.support.PageFactory;

import java.util.List;

public class OrderHistoryPage extends AbstractComponent {
    WebDriver driver;
    public OrderHistoryPage(WebDriver driver){
        super(driver);
        this.driver = driver;
        PageFactory.initElements(driver,this);
    }

    @FindBy(css = "td:nth-child(3)")
    List<WebElement> orderedProducts;

    public Boolean verifyOrderDisplay(String productName){
        Boolean matched = orderedProducts.stream().anyMatch(product -> product.getText().equalsIgnoreCase(productName));
        return  matched;

    }
}
