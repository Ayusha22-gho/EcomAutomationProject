package org.ecomautomation.Tests;

import ecomautomation.pageObjectClass.*;
import org.ecomautomation.TestComponents.BaseTest;
import org.openqa.selenium.WebElement;
import org.testng.Assert;
import org.testng.annotations.DataProvider;
import org.testng.annotations.Test;

import java.io.IOException;
import java.util.List;

public class StandAloneTest extends BaseTest {

    String productName = "ZARA COAT 3";
    @Test(dataProvider = "getData", groups ={"Purchase"})
    public void submitOrder(String email, String pass, String productName) throws IOException {

        ProductCatalogue pdp = landingPage.loginApplication(email,pass);
        List<WebElement> products = pdp.getProductList();
        pdp.addProducToCart(productName);
        CartPage cart = pdp.goToCartPage();

        Boolean matchedItem = cart.getCartMatchedItem(productName);
        Assert.assertTrue(matchedItem);

        ShippingPage ship = cart.clickCheckout();

         ship.selectCountry("india");
        OrderConfirmation order = ship.placeOrder();

        String confirmationMessage = order.orderConfirm();
        Assert.assertTrue(confirmationMessage.equalsIgnoreCase("Thankyou for the order."));

    }

    @Test(dependsOnMethods = {"submitOrder"})
    public void orderHistoryTest(){
        ProductCatalogue pdp = landingPage.loginApplication("ayghosh977@gmail.com","Rules123");
        OrderHistoryPage orderHistory = pdp.goToOrderHistoryPage();
        Assert.assertTrue(orderHistory.verifyOrderDisplay(productName));
    }

    @DataProvider
    public Object[][] getData(){
       Object[][] data =  new Object[][] {{"ayghosh977@gmail.com","Rules123","ZARA COAT 3"},
               {"jiyaghosh879@gmail.com","Rules123","ADIDAS ORIGINAL"}};

       return data;
    }
}
