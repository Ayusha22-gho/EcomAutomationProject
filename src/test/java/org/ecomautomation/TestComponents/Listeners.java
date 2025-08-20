package org.ecomautomation.TestComponents;

import com.aventstack.extentreports.ExtentReports;
import com.aventstack.extentreports.ExtentTest;
import com.aventstack.extentreports.Status;
import ecomautomation.resources.ExtentReporterEngine;
import org.openqa.selenium.WebDriver;
import org.testng.ITestContext;
import org.testng.ITestListener;
import org.testng.ITestResult;

import java.io.IOException;

public class Listeners extends BaseTest implements ITestListener {

    // This class can be used to implement test listeners for logging, reporting, etc.
    // Currently, it does not contain any methods, but you can override methods from ITestListener
    // to handle events like test start, test success, test failure, etc.

    ExtentReports extent = ExtentReporterEngine.getReportObject();
    ExtentTest test;
    ThreadLocal<ExtentTest> extentTest = new ThreadLocal();
     // You can override methods from ITestListener to perform actions at different stages of the test execution.
     // For example, you can log messages, take screenshots, or generate reports based on test results.
     // Below are some examples of how to override these methods:
    // Example:
     @Override
     public void onTestStart(ITestResult result) {
         System.out.println("Test started: " + result.getName());
         test = extent.createTest(result.getMethod().getMethodName());
         extentTest.set(test);//assign unique thread id->test (like a map)
         //knows which test is actually running
     }

     @Override
    public void onTestSuccess(ITestResult result){
         test.log(Status.PASS, "Test passed: " + result.getName());
     }
    @Override
    public void onTestFailure(ITestResult result) {
       // test.log(Status.FAIL, "Test failed: " + result.getName());
       extentTest.get().log(Status.FAIL, "Test failed: " + result.getName());
        // test.fail(result.getThrowable());
        extentTest.get().fail(result.getThrowable());
        // You can also take a screenshot here if needed
        // For example:
        try {
            driver = (WebDriver) result.getTestClass().getRealClass()
                    .getField("driver").get(result.getInstance());
        } catch (NoSuchFieldException e) {
            throw new RuntimeException(e);
        } catch (IllegalAccessException e) {
            throw new RuntimeException(e);
        }
        String screenshotPath = null;
        try {
            screenshotPath = getScreenshot(result.getMethod().getMethodName(),driver);
        } catch (IOException e) {
            throw new RuntimeException(e);
        }
        extentTest.get().addScreenCaptureFromPath(screenshotPath,result.getMethod().getMethodName());

    }

    @Override
    public void onTestSkipped(ITestResult result){
        extentTest.get().log(Status.SKIP, "Test skipped: " + result.getName());
        extentTest.get().skip(result.getThrowable());
    }

    @Override
    public void onFinish(ITestContext result) {
        extent.flush(); // This will write the report to the specified file
        System.out.println("All tests finished.");
    }
}
