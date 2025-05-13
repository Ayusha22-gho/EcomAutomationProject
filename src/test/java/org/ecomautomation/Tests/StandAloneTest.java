package org.ecomautomation.Tests;

import ecomautomation.pageObjectClass.*;
import org.ecomautomation.TestComponents.BaseTest;
import org.openqa.selenium.WebElement;
import org.testng.Assert;
import org.testng.annotations.Test;

import java.io.IOException;
import java.util.List;

public class StandAloneTest extends BaseTest {

    @Test
    public void submitOrder() throws IOException {
        String productName = "ZARA COAT 3";
        ProductCatalogue pdp = landingPage.loginApplication("ayghosh977@gmail.com","Rules123");
        List<WebElement> products = pdp.getProductList();
        CartPage cart = pdp.addProducToCart(productName);


        Boolean matchedItem = cart.getCartMatchedItem(productName);
        Assert.assertTrue(matchedItem);

        ShippingPage ship = cart.clickCheckout();

         ship.selectCountry("india");
        OrderConfirmation order = ship.placeOrder();

        String confirmationMessage = order.orderConfirm();
        Assert.assertTrue(confirmationMessage.equalsIgnoreCase("Thankyou for the order."));

    }
}
