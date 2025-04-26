package ecomautomation.pageObjectClass;

import ecomautomation.AbstarctComponents.AbstractComponent;
import org.openqa.selenium.WebDriver;
import org.openqa.selenium.WebElement;
import org.openqa.selenium.support.FindBy;
import org.openqa.selenium.support.PageFactory;

public class LandingPage extends AbstractComponent {
   //we could have use object of abstract class but that will create overhead memory
    WebDriver driver;

    public LandingPage(WebDriver driver){
        //child t parent pass variables
        super(driver);
        this.driver = driver;
        PageFactory.initElements(driver,this);
    }
    //WebElement userEmail =  driver.findElement(By.id("userEmail"));

    //Design Pattern -> Page Factory
    //Go and initialize all the elements, doing so it needs driver
    //pagefactory will initailize the driver
    @FindBy(id = "userEmail")
    WebElement userEmail;

    @FindBy(id = "userPassword")
    WebElement password;

    @FindBy(id = "login")
    WebElement submit;

    public void loginApplication(String email, String pass){
         userEmail.sendKeys(email);
         password.sendKeys(pass);
         submit.click();
    }

    public void goTo(){
        driver.get("https://rahulshettyacademy.com/client/");
    }


}
