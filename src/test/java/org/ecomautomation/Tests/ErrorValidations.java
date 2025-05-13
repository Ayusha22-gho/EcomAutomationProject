package org.ecomautomation.Tests;

import ecomautomation.pageObjectClass.ProductCatalogue;
import org.ecomautomation.TestComponents.BaseTest;
import org.testng.Assert;
import org.testng.annotations.Test;

public class ErrorValidations extends BaseTest {

    @Test
    public void login(){
        ProductCatalogue pdp = landingPage.loginApplication("ayghosh977@gmail.com","sample");
        Assert.assertEquals("Incorrect email or password.",landingPage.getErrorMessage());

    }
}
