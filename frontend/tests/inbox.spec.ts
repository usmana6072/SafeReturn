import {test,expect} from "@playwright/test";
test.setTimeout(90000);
test("private inbox controls, settings and help",async({page})=>{
 await page.goto('/inbox');await expect(page).toHaveURL(/login/);
 await page.getByLabel('Email address').fill('inbox@example.invalid');await page.locator('input[name="password"]').fill('synthetic-password');
 await page.getByRole('button',{name:'Log in',exact:true}).click();await expect(page).toHaveURL(/account/);
 await page.goto('/settings');await expect(page.getByRole('heading',{name:'Settings',exact:true})).toBeVisible();
 await expect(page.getByRole('heading',{name:'Consent history',exact:true})).toBeVisible();
 await page.getByLabel('I confirm that I want an account-deletion review.').check();
 await page.getByRole('button',{name:'Submit deletion request',exact:true}).click();
 await expect(page.getByRole('status')).toContainText('saved for review');
 await page.goto('/help');await expect(page.getByRole('heading',{name:'Help',exact:true})).toBeVisible();
 await page.goto('/inbox');await expect(page.getByRole('heading',{name:'Finder inbox',exact:true})).toBeVisible();
 await page.goto('/inbox/'+process.env.TASK57_MESSAGE);await expect(page.getByText('SYNTHETIC PRIVATE MESSAGE',{exact:true})).toBeVisible();
 await page.getByLabel('Message status',{exact:true}).selectOption('flagged');await page.getByRole('button',{name:'Save status',exact:true}).click();
 await expect(page.getByRole('status')).toContainText('Changes saved');
 await page.getByLabel('I want to delete this message.').check();await page.getByRole('button',{name:'Delete message',exact:true}).click();
 await expect(page).toHaveURL(/inbox\?result=deleted/);await expect(page.getByRole('status')).toContainText('removed');
 expect(await page.evaluate(()=>localStorage.length+sessionStorage.length)).toBe(0);
});

test("public help works in Urdu on mobile without JavaScript",async({browser})=>{
 const context=await browser.newContext({javaScriptEnabled:false,viewport:{width:375,height:812}});
 await context.addCookies([{name:'safereturn-language',value:'ur',url:'http://127.0.0.1:3100'}]);
 const page=await context.newPage();await page.goto('/help');
 await expect(page).toHaveURL(/help/);await expect(page.locator('html')).toHaveAttribute('dir','rtl');
 await expect(page.getByRole('heading',{name:'مدد',exact:true})).toBeVisible();
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
 await context.close();
});
