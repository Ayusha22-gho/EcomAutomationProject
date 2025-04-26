package ecomautomation.pageObjectClass;

import ecomautomation.AbstarctComponents.AbstractComponent;
import org.openqa.selenium.By;
import org.openqa.selenium.WebDriver;
import org.openqa.selenium.WebElement;
import org.openqa.selenium.support.FindBy;
import org.openqa.selenium.support.PageFactory;

import java.util.List;

public class ProductCatalogue extends AbstractComponent {

    WebDriver driver;

    public ProductCatalogue(WebDriver driver){
        super(driver);
        this.driver = driver;
        PageFactory.initElements(driver,this);
    }
    //WebElement userEmail =  driver.findElement(By.id("userEmail"));

    //Design Pattern -> Page Factory
    //Go and initialize all the elements, doing so it needs driver
    //pagefactory will initailize the driver
    @FindBy(css = ".mb-3")
        List<WebElement> products;
    @FindBy(css = ".ng-animating")
        WebElement spinner;

    By productsElement = By.cssSelector(".mb-3");

    By addToCart = By.cssSelector(".card-body button:last-of-type");
    By toastMessage = By.cssSelector("#toast-container");


    public List<WebElement> getProductList(){
    waitForElementToAppear(productsElement);
    return products;
    }

    public WebElement getProductByName(String productName){
        WebElement prod = getProductList().stream().filter(product ->
                product.findElement(By.cssSelector("b")).getText().equals(productName)).findFirst().orElse(null);
        return prod;
    }

    public CartPage addProducToCart(String productName){
        //this add to card element is within the scope of the prod element therefore
        //we are not using driver.finfElement and using getProductByName(productName).findElement
        WebElement prod = getProductByName(productName);
        prod.findElement(addToCart).click();
        waitForElementToAppear(toastMessage);
        waitForElementToDisappear(spinner);
        CartPage cart = new CartPage(driver);
        return cart;

    }

}
