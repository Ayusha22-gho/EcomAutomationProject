package ecomautomation.pageObjectClass;

import ecomautomation.AbstarctComponents.AbstractComponent;
import org.openqa.selenium.By;
import org.openqa.selenium.JavascriptExecutor;
import org.openqa.selenium.WebDriver;
import org.openqa.selenium.WebElement;
import org.openqa.selenium.support.FindBy;
import org.openqa.selenium.support.PageFactory;

public class ShippingPage extends AbstractComponent {
    WebDriver driver;

    @FindBy(css = "input[placeholder='Select Country']")
    WebElement shippingCountry;
    @FindBy(xpath = "(//*[contains(@class,'ta-results')]/button)[2]")
            WebElement selectCountry;
   @FindBy(css = ".action__submit")
           WebElement placeOrderButton;
    By countryResults = By.cssSelector(".ta-results");

    public ShippingPage(WebDriver driver) {
        super(driver);
        this.driver = driver;
        PageFactory.initElements(driver,this);
    }

    public void selectCountry(String country){
        shippingCountry.sendKeys(country);
        waitForElementToAppear(countryResults);
        JavascriptExecutor js = (JavascriptExecutor) driver;
        js.executeScript("arguments[0].click()",selectCountry);
    }

    public OrderConfirmation placeOrder(){
        JavascriptExecutor js = (JavascriptExecutor) driver;
        js.executeScript("arguments[0].click()",placeOrderButton);
        OrderConfirmation order = new OrderConfirmation(driver);
        return order;
    }
}
