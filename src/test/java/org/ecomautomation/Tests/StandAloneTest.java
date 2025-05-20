package org.ecomautomation.Tests;

import ecomautomation.pageObjectClass.*;
import org.ecomautomation.TestComponents.BaseTest;
import org.openqa.selenium.WebElement;
import org.testng.Assert;
import org.testng.annotations.DataProvider;
import org.testng.annotations.Test;

import java.io.IOException;
import java.util.HashMap;
import java.util.List;

public class StandAloneTest extends BaseTest {

    String productName = "ZARA COAT 3";
    @Test(dataProvider = "getHashData", groups ={"Purchase"})
    public void submitOrder(HashMap<String,String> inputs) throws IOException {

        ProductCatalogue pdp = landingPage.loginApplication(inputs.get("email"),inputs.get("password"));
        List<WebElement> products = pdp.getProductList();
        pdp.addProducToCart(inputs.get("product"));
        CartPage cart = pdp.goToCartPage();

        Boolean matchedItem = cart.getCartMatchedItem(inputs.get("product"));
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

    @DataProvider
    public Object[][] getHashData(){
        HashMap<String,String> map = new HashMap<>();
        map.put("email","ayghosh977@gmail.com");
        map.put("password","Rules123");
        map.put("product","ZARA COAT 3");

        HashMap<String,String> map1 = new HashMap<>();
        map1.put("email","jiyaghosh879@gmail.com");
        map1.put("password","Rules123");
        map1.put("product","ADIDAS ORIGINAL");

        return new Object[][] {{map},{map1}};
    }
}
