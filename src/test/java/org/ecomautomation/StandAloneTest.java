package org.ecomautomation;

import ecomautomation.pageObjectClass.*;
import io.cucumber.java.et.Ja;
import io.github.bonigarcia.wdm.WebDriverManager;
import org.openqa.selenium.By;
import org.openqa.selenium.JavascriptExecutor;
import org.openqa.selenium.WebDriver;
import org.openqa.selenium.WebElement;
import org.openqa.selenium.chrome.ChromeDriver;
import org.openqa.selenium.interactions.Actions;
import org.openqa.selenium.support.ui.ExpectedConditions;
import org.openqa.selenium.support.ui.WebDriverWait;
import org.testng.Assert;

import java.time.Duration;
import java.util.List;

public class StandAloneTest {
    public static void main(String[] args){
        String productName = "ZARA COAT 3";
        WebDriverManager.chromedriver().setup();
        WebDriver driver = new ChromeDriver();
        driver.manage().timeouts().implicitlyWait(Duration.ofSeconds(10));
        driver.manage().window().maximize();

        LandingPage landingPage = new LandingPage(driver);
        landingPage.goTo();
        landingPage.loginApplication("ayghosh977@gmail.com","Rules123");

        ProductCatalogue pdp = new ProductCatalogue(driver);
        List<WebElement> products = pdp.getProductList();
        pdp.addProducToCart(productName);

        CartPage cart = new CartPage(driver);
        Boolean matchedItem = cart.getCartMatchedItem(productName);
        Assert.assertTrue(matchedItem);
        cart.clickCheckout();

        ShippingPage ship = new ShippingPage(driver);
        ship.selectCountry("india");

        OrderConfirmation order = new OrderConfirmation(driver);
        String confirmationMessage = order.orderConfirm();
        Assert.assertTrue(confirmationMessage.equalsIgnoreCase("Thankyou for the order."));

        //-------------Login Application ----------------//
        //driver.get("https://rahulshettyacademy.com/client/");
//        driver.findElement(By.id("userEmail")).sendKeys("ayghosh977@gmail.com");
//        driver.findElement(By.id("userPassword")).sendKeys("Rules123");
//        driver.findElement(By.id("login")).click();

        //----------------Product List, Selecting one product and adding to cart --------------//
//        WebDriverWait wait = new WebDriverWait(driver, Duration.ofSeconds(5));
//        wait.until(ExpectedConditions.visibilityOfElementLocated(By.cssSelector(".mb-3")));
//        List<WebElement> products = driver.findElements(By.cssSelector(".mb-3"));
        //we will use streams
        //System.out.println("products are" +products);

//        WebElement prod = products.stream().filter(product ->
//                product.findElement(By.cssSelector("b")).getText().equals(productName)).findFirst().orElse(null);

        //-----------Iterating product through loop ----------//
//        for(WebElement prod : products){
//            if(prod.findElement(By.cssSelector("b")).getText().equals("ZARA COAT 3")){
//                prod.findElement(By.cssSelector(".card-body button:last-of-type")).click();
//            }
//            else{
//                prod = null;
//            }
//            }
//
//         prod.findElement(By.cssSelector(".card-body button:last-of-type")).click();
        //wait.until(ExpectedConditions.visibilityOfElementLocated(By.cssSelector("#toast-container")));
        //wait.until(ExpectedConditions.invisibilityOf(driver.findElement(By.cssSelector(".ng-animating"))));

//-------------------------------Clic cart Page and click checkout
//        driver.findElement(By.cssSelector("[routerlink*=\"cart\"]")).click();
//
//        wait.until(ExpectedConditions.visibilityOfElementLocated(By.cssSelector(".cartSection h3")));
//        List<WebElement> cartItems = driver.findElements(By.cssSelector(".cartSection h3"));
//        Boolean matchedItem = cartItems.stream().anyMatch(cartItem -> cartItem.getText().equals(productName));
//        Assert.assertTrue(matchedItem);
//
//        JavascriptExecutor js = (JavascriptExecutor) driver;
//        js.executeScript("arguments[0].click()",driver.findElement(By.cssSelector(".totalRow button")));
        //driver.findElement(By.cssSelector(".totalRow button")).click();

        //----------------Shipping Page---------------------//
//        Actions action = new Actions(driver);
//        action.sendKeys(driver.findElement(By.cssSelector("input[placeholder='Select Country']")),"india").build().perform();
//        driver.findElement(By.cssSelector("input[placeholder='Select Country']")).sendKeys("india");
//        wait.until(ExpectedConditions.visibilityOfElementLocated(By.cssSelector(".ta-results")));

       //driver.findElement(By.xpath("(//*[contains(@class,'ta-results')]/button)[2]")).click();
  //      js.executeScript("arguments[0].click()",driver.findElement(By.xpath("(//*[contains(@class,'ta-results')]/button)[2]")));
       // driver.findElement(By.cssSelector(".action__submit")).click();
   //     js.executeScript("arguments[0].click()",driver.findElement(By.cssSelector(".action__submit")));

     //---------------------OrderConfirmationPage-------------------//
      //  String confirmationMessage = driver.findElement(By.cssSelector(".hero-primary")).getText();
       // Assert.assertTrue(confirmationMessage.equalsIgnoreCase("Thankyou for the order."));
       //driver.close();
    }
}
