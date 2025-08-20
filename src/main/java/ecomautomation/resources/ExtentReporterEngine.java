package ecomautomation.resources;

import com.aventstack.extentreports.ExtentReports;
import com.aventstack.extentreports.reporter.ExtentSparkReporter;

public class ExtentReporterEngine {

    public static ExtentReports getReportObject() {
        // Implementation for generating the report object
        // This could include setting up the report, adding configurations, etc.
        String path = System.getProperty("user.dir") + "//reports//index.html";
        ExtentSparkReporter spark = new ExtentSparkReporter(path);
        spark.config().setReportName("E-Commerce Automation Results");
        spark.config().setDocumentTitle("Test Results");
        spark.config().setTheme(com.aventstack.extentreports.reporter.configuration.Theme.DARK);

        ExtentReports extent = new ExtentReports();
        extent.attachReporter(spark);
        extent.setSystemInfo("Tester", "Ayusha Ghosh");
        return extent;
    }
}
