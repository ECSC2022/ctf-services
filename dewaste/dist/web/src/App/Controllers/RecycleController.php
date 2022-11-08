<?php

namespace App\Controllers;

use App\Model\DigitalItem;
use App\Model\DuplicateEmailAddressException;
use App\Model\DuplicateSerialNumberException;
use App\Model\PhysicalItem;
use App\Model\Redirection;
use App\Model\Route;
use App\Model\User;
use App\Routes;
use App\Service\DigitalItemRegistrationService;
use App\Service\DigitalItemService;
use App\Service\PhysicalItemRegistrationService;
use App\Service\PhysicalItemService;
use App\Service\SessionService;
use App\Service\UserCreationService;
use App\Service\UserLoginService;
use App\UI\Template;
use AssertionError;

class RecycleController
{
    public function __construct(
        private readonly Template $template,
        private readonly SessionService $sessionService,
        private readonly UserLoginService $userLoginService,
        private readonly UserCreationService $userCreationService,
        private readonly PhysicalItemRegistrationService $physicalItemRegistrationService,
        private readonly PhysicalItemService $physicalItemService,
        private readonly DigitalItemService $digitalItemService,
        private readonly DigitalItemRegistrationService $digitalItemRegistrationService,
        private readonly int $maximumFileSize,
    ) {
    }

    #[Route(Routes::RECYCLE_PHYSICAL_REGISTER, [Route::GET, Route::POST])]
    public function physicalRegistration(): string
    {
        $realUser = $this->sessionService->getUser();
        $user = null;
        $item = null;
        $userType = null;
        $msg = "";
        $loginEmail = "";

        if (isPostRequest()) {
            $formData = $this->parsePhysicalRegistrationForm();
            $user = $formData["newUser"];
            $item = $formData["item"];
            $userType = $formData["userType"];
            $loginEmail = $formData["login"]["email"];

            $msg = $this->handlePhysicalRegistrationPost(
                $item,
                $realUser,
                $userType,
                $formData["login"],
                $user,
                $formData["newPassword"]
            );
        }

        $content = $this->template->dynamicTemplate(
            "recycle/physical_registration_form.php",
            user: $user,
            item: $item,
            loggedIn: $realUser !== null,
            userType: $userType,
            message: $msg,
            loginEmail: $loginEmail
        );
        return $this->withRegistrationTemplate("Registration | Physical", $content, "physical");
    }

    /**
     * @param User|null $realUser
     * @param string $userType
     * @param array{email:string,password:string} $loginInfo
     * @param User $user
     * @param string $newPassword
     * @return string|User|null
     */
    private function handleUserAccountWhenRegistering(
        ?User $realUser,
        string $userType,
        array $loginInfo,
        User $user,
        string $newPassword
    ): string|User|null {
        if ($realUser === null && $userType === "account") {
            if (trim($loginInfo["email"]) !== "" && $loginInfo["password"] !== "") {
                $realUser = $this->userLoginService->login(trim($loginInfo["email"]), $loginInfo["password"]);
                if ($realUser === null) {
                    return errorBox("E-Mail address or password is incorrect");
                }
            } else {
                if (($msg = $user->validate()) !== true) {
                    return errorBox($msg);
                }

                try {
                    $realUser = $this->userCreationService->create($user, $newPassword);
                } catch (\InvalidArgumentException $e) {
                    return errorBox($e->getMessage());
                } catch (DuplicateEmailAddressException) {
                    return errorBox("A user with this email address already exists.");
                }
            }
        }
        return $realUser;
    }

    /**
     * @param PhysicalItem $item
     * @param User|null $realUser
     * @param string $userType
     * @param array{email:string,password:string} $loginInfo
     * @param User $user
     * @param string $newPassword
     * @return string
     */
    private function handlePhysicalRegistrationPost(
        PhysicalItem $item,
        ?User &$realUser,
        string $userType,
        array $loginInfo,
        User $user,
        string $newPassword
    ): string {
        if (($msg = $item->validate()) !== true) {
            return errorBox($msg);
        }

        $newUser = $this->handleUserAccountWhenRegistering($realUser, $userType, $loginInfo, $user, $newPassword);
        if (is_string($newUser)) {
            return $newUser;
        }
        $realUser = $newUser;

        try {
            $this->physicalItemRegistrationService->register($item, $realUser);
        } catch (DuplicateSerialNumberException) {
            return errorBox("Serial number is already registered.");
        }

        if ($item->id === null) {
            throw new AssertionError("The item was not created successfully (no id set)");
        }

        if ($realUser !== null) {
            throw new Redirection(Routes::recycleMyItemsPhysical($item->id));
        }

        $accessLink = BASEURL . Routes::recycleMyItemsPhysical($item->id, $item->authToken);
        return <<<HTML
<p class="alert alert-success">
Item successfully registered.
Please come to our facility in the next few days.

To follow the status of your item you can visit the link:
<a href="$accessLink">$accessLink</a>
</p>
HTML;
    }

    /**
     * @return array{
     *     item:PhysicalItem,
     *     userType:string,
     *     login:array{email:string,password:string},
     *     newUser:User,
     *     newPassword:string
     * }
     */
    private function parsePhysicalRegistrationForm(): array
    {
        return [
            "item" => new PhysicalItem(
                null,
                parsePostString("serial") ?? "",
                parsePostString("item_description") ?? "",
                parsePostInt("length") ?? 0,
                parsePostInt("width") ?? 0,
                parsePostInt("height") ?? 0,
                parsePostFloat("weight") ?? 0,
            ),
            ...$this->parseAccountForm()
        ];
    }

    /**
     * @return array{
     *     item:DigitalItem,
     *     file:array{error:int,tmp_name:string,name:string}|null,
     *     userType:string,
     *     login:array{email:string,password:string},
     *     newUser:User,
     *     newPassword:string
     * }
     */
    private function parseDigitalRegistrationForm(): array
    {
        return [
            "item" => new DigitalItem(
                null,
                "",
                parsePostString("item_description") ?? "",
                0,
            ),
            "file" => $_FILES["datafile"] ?? null,
            ...$this->parseAccountForm()
        ];
    }

    /**
     * @return array{userType:string,login:array{email:string,password:string},newUser:User,newPassword:string}
     */
    private function parseAccountForm(): array
    {
        return [
            "userType" => parsePostString("auth_type") ?? "",
            "login" => [
                "email" => parsePostString("email") ?? "",
                "password" => parsePostString("password") ?? ""
            ],
            "newUser" => User::create(
                parsePostString("newEmail") ?? "",
                parsePostString("newFirstname") ?? "",
                parsePostString("newLastname") ?? ""
            ),
            "newPassword" => parsePostString("newPassword") ?? ""
        ];
    }

    #[Route(Routes::RECYCLE_DIGITAL_REGISTER, [Route::GET, Route::POST])]
    public function digitalRegistration(): string
    {
        $realUser = $this->sessionService->getUser();
        $user = null;
        $item = null;
        $userType = null;
        $msg = "";
        $loginEmail = "";

        if (isPostRequest()) {
            $formData = $this->parseDigitalRegistrationForm();
            $user = $formData["newUser"];
            $item = $formData["item"];
            $userType = $formData["userType"];
            $loginEmail = $formData["login"]["email"];
            $file = $formData["file"];

            $msg = $this->handleDigitalRegistrationPost(
                $item,
                $realUser,
                $userType,
                $formData["login"],
                $user,
                $formData["newPassword"],
                $file
            );
        }

        $content = $this->template->dynamicTemplate(
            "recycle/digital_registration_form.php",
            user: $user,
            item: $item,
            loggedIn: $realUser !== null,
            userType: $userType,
            message: $msg,
            loginEmail: $loginEmail,
            maxFileSize: $this->maximumFileSize,
        );
        return $this->withRegistrationTemplate("Registration | Digital", $content, "digital");
    }

    private function withRegistrationTemplate(string $title, string $content, string $active = ""): string
    {
        $recycleTemplate = $this->template->dynamicTemplate(
            "recycle/registration_template.php",
            content: $content,
            active: $active
        );
        return $this->template->withMainLayout($title, $recycleTemplate);
    }

    #[Route(Routes::RECYCLE_MYITEMS)]
    public function myItems(): string
    {
        $user = $this->sessionService->getUser();
        if ($user === null) {
            throw new Redirection(Routes::USER_LOGIN);
        }

        if ($user->id === null) {
            throw new AssertionError("User ID not defined");
        }

        $physicalItems = $this->physicalItemService->getByUserId($user->id);
        $digitalItems = $this->digitalItemService->getByUserId($user->id);

        $myItemsTemplate = $this->template->dynamicTemplate(
            "recycle/myitems_list.php",
            physicalItems: $physicalItems,
            digitalItems: $digitalItems,
        );
        return $this->template->withMainLayout("My Items", $myItemsTemplate);
    }

    /**
     * @param array{1:numeric-string} $params
     * @return string
     */
    #[Route(Routes::_RECYCLE_MYITEMS_PHYSICAL)]
    public function myPhysicalItem(array $params): string
    {
        $itemId = (int) $params[1];

        $authToken = parseGetString("authToken", null);

        $physicalItem = $this->physicalItemService->getById($itemId);
        if ($physicalItem === null) {
            http_response_code(404);
            return errorBox("Item does not exist");
        }

        $ownerIds = $this->physicalItemService->getOwnerIds($itemId);

        $user = $this->sessionService->getUser();
        if ($user !== null && in_array($user->id, $ownerIds)) {
            // all good
        } elseif ($authToken !== null && $physicalItem->authToken === $authToken) {
            // all good
        } else {
            throw new Redirection(Routes::USER_LOGIN);
        }

        $myItemsTemplate = $this->template->dynamicTemplate(
            "recycle/myitem_physical.php",
            item: $physicalItem
        );
        return $this->template->withMainLayout("My Item | " . $physicalItem->serial, $myItemsTemplate);
    }

    /**
     * @param array{1:numeric-string} $params
     * @return string
     */
    #[Route(Routes::_RECYCLE_MYITEMS_DIGITAL)]
    public function myDigitalItem(array $params): string
    {
        $itemId = (int) $params[1];

        $authToken = parseGetString("authToken", null);

        $digitalItem = $this->digitalItemService->getById($itemId);
        if ($digitalItem === null) {
            http_response_code(404);
            return errorBox("Item does not exist");
        }

        $ownerIds = $this->digitalItemService->getOwnerIds($itemId);

        $user = $this->sessionService->getUser();
        if ($user !== null && in_array($user->id, $ownerIds)) {
            // all good
        } elseif ($authToken !== null && $digitalItem->authToken === $authToken) {
            // all good
        } else {
            throw new Redirection(Routes::USER_LOGIN);
        }

        $analysisResults = $this->digitalItemService->getAnalysisResults($itemId);

        $myItemsTemplate = $this->template->dynamicTemplate(
            "recycle/myitem_digital.php",
            item: $digitalItem,
            authToken: $authToken,
            analysisResults: $analysisResults,
        );
        return $this->template->withMainLayout("My Item", $myItemsTemplate);
    }

    /**
     * @param DigitalItem $item
     * @param User|null $realUser
     * @param string $userType
     * @param array{email:string,password:string} $loginInfo
     * @param User $user
     * @param string $newPassword
     * @param array{error:int,tmp_name:string,name:string}|null $file
     * @return string
     */
    private function handleDigitalRegistrationPost(
        DigitalItem $item,
        ?User &$realUser,
        string $userType,
        array $loginInfo,
        User $user,
        string $newPassword,
        ?array $file,
    ): string {
        if (($msg = $item->validate()) !== true) {
            return errorBox($msg);
        }

        if ($file === null || $file["error"] !== UPLOAD_ERR_OK) {
            return errorBox("Could not upload image");
        }

        $item->size = filesize($file["tmp_name"]) ?: 0;
        if ($item->size > $this->maximumFileSize) {
            return errorBox("File too large. (maximum = " . ($this->maximumFileSize / 1000) . "KB)");
        }

        $ext = pathinfo($file["name"], PATHINFO_EXTENSION);
        $extLen = strlen($ext);
        if ($extLen > 5) {
            return errorBox("File extension invalid");
        }
        $name = substr($file["name"], 0, 100 - $extLen - 1);
        if ($ext && str_ends_with($name, $ext)) {
            $name = substr($name, 0, -$extLen);
        }
        $item->name = "$name$ext";

        $content = file_get_contents($file["tmp_name"]);
        if ($content === false) {
            return errorBox("Could not read file");
        }

        $newUser = $this->handleUserAccountWhenRegistering($realUser, $userType, $loginInfo, $user, $newPassword);
        if (is_string($newUser)) {
            return $newUser;
        }

        $realUser = $newUser;
        $this->digitalItemRegistrationService->register($item, $content, $realUser);

        if ($item->id === null) {
            throw new AssertionError("Item not registered correctly (id not set)");
        }

        if ($realUser !== null) {
            throw new Redirection(Routes::recycleMyItemsDigital($item->id));
        }

        $accessLink = BASEURL . Routes::recycleMyItemsDigital($item->id, $item->authToken);
        return <<<HTML
<p class="alert alert-success">
Item successfully registered.
We will look into your data soon.

To follow the status of your item you can visit the link:
<a href="$accessLink">$accessLink</a>
</p>
HTML;
    }

    /**
     * @param array{1:numeric-string} $params
     * @return string
     */
    #[Route(Routes::_DIGITAL_ITEM_DOWNLOAD)]
    public function digitalItemDownload(array $params): string
    {
        $itemId = (int) $params[1];

        $authToken = parseGetString("authToken", null);

        $digitalItem = $this->digitalItemService->getById($itemId);
        if ($digitalItem === null) {
            http_response_code(404);
            return errorBox("Item does not exist");
        }

        $ownerIds = $this->digitalItemService->getOwnerIds($itemId);

        $user = $this->sessionService->getUser();
        if ($user !== null && in_array($user->id, $ownerIds)) {
            // all good
        } elseif ($authToken !== null && $digitalItem->authToken === $authToken) {
            // all good
        } else {
            throw new Redirection(Routes::USER_LOGIN);
        }

        $content = $this->digitalItemService->getContent($itemId);
        if ($content === null) {
            http_response_code(404);
            return errorBox("Item has no content");
        }

        header('Content-Disposition: attachment; filename="' . $digitalItem->name . '"');
        return $content;
    }
}
