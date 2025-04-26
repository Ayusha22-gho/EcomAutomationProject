package ecomautomation.pageObjectClass;

import ecomautomation.AbstarctComponents.AbstractComponent;
import org.openqa.selenium.By;
import org.openqa.selenium.JavascriptExecutor;
import org.openqa.selenium.WebDriver;
import org.openqa.selenium.WebElement;
import org.openqa.selenium.support.FindBy;
import org.openqa.selenium.support.PageFactory;

import java.util.List;

public class CartPage extends AbstractComponent {
    WebDriver driver;

    public CartPage(WebDriver driver) {
        super(driver);
        this.driver = driver;
        PageFactory.initElements(driver,this);
    }



    @FindBy(css = ".cartSection h3")
    private List<WebElement> cartItems;

    By cartItemSection = By.cssSelector(".cartSection h3");

    @FindBy(css = ".totalRow button")
    WebElement checkoutButton;

    public Boolean getCartMatchedItem(String productName){
        goToCartPage();
        waitForElementToAppear(cartItemSection);
        Boolean matchedItem = cartItems.stream().anyMatch(cartItem -> cartItem.getText().equals(productName));
        return matchedItem;
    }

    public void clickCheckout(){
        JavascriptExecutor js = (JavascriptExecutor) driver;
        js.executeScript("arguments[0].click()",checkoutButton);
    }
}
