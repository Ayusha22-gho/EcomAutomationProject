package org.ecomautomation.Tests;

import ecomautomation.pageObjectClass.CartPage;
import ecomautomation.pageObjectClass.ProductCatalogue;
import org.ecomautomation.TestComponents.BaseTest;
import org.openqa.selenium.WebElement;
import org.testng.Assert;
import org.testng.annotations.Test;

import java.io.IOException;
import java.util.List;

public class ErrorValidationTest extends BaseTest {

    @Test
    public void loginErrorValidation(){
        ProductCatalogue pdp = landingPage.loginApplication("ayghosh977@gmail.com","sample");
        Assert.assertEquals("Incorrect email or password.",landingPage.getErrorMessage());

    }

    @Test(groups = {"ErrorHandling"})
    public void productErrorValidation() throws IOException {
        String productName = "ZARA COAT 3";
        ProductCatalogue pdp = landingPage.loginApplication("ayghosh977@gmail.com","Rules123");
        List<WebElement> products = pdp.getProductList();
        pdp.addProducToCart(productName);
        CartPage cart = pdp.goToCartPage();
        Boolean matchedItem = cart.getCartMatchedItem(productName);
        Assert.assertFalse(matchedItem);

    }
}
