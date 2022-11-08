<?php

use App\Model\DigitalItem;
use App\Model\User;

/** @var DigitalItem|null $item */
$item ??= null;
/** @var bool|null $loggedIn */
$loggedIn ??= false;
/** @var string|null $userType */
$userType ??= "account";
/** @var User|null $user */
$user ??= null;
/** @var string|null $message */
$message ??= "";
/** @var string|null $loginEmail */
$loginEmail ??= "";
/** @var int|null $maxFileSize */
$maxFileSize ??= 2 * 1000 * 1000;

$_ = fn(string $unsafe) => htmlspecialchars($unsafe, ENT_QUOTES);
$checkedIf = fn(bool $checked) => $checked ? "checked" : "";
$itemVal = fn(string $name) => $_($item?->$name ?? "");
$userVal = fn(string $name) => $_($user?->$name ?? "");
?>

<h3>Digital item upload</h3>
<?= $message ?>
<form class="recycle-form" method="post" enctype="multipart/form-data">
    <fieldset>
        <h4>Basic information</h4>
        <div class="form-group">
            <label for="item_description" class="form-label">Item description / Good to know</label>
            <textarea class="form-control" id="item_description" name="item_description"
            ><?= $itemVal("description") ?></textarea>
        </div>
    </fieldset>
    <fieldset>
        <h4>File</h4>

        <div class="form-group row">
            <div class="col-9">
                <label for="datafile" class="form-label">File</label>
                <input type="file" id="datafile" name="datafile" class="form-control" required
                    data-max-size="<?= $maxFileSize ?>" data-size-update-target="#size"/>
                <span class="form-text">Maximum file size: <?= number_format($maxFileSize / 1000) ?>KB</span>
            </div>
            <div class="col">
                <label for="size" class="form-label">Size<span class="unit">(in kB)</span></label>
                <input type="text" id="size" name="size" class="form-control" readonly/>
            </div>
        </div>
    </fieldset>

    <?php
    include __DIR__ . "/account_registration.php";
    ?>

    <div class="d-flex justify-content-center mb-3">
        <div class="form-check">
            <input type="checkbox" class="form-check-input" id="conditions_accept" required/>
            <label for="conditions_accept">I accept the conditions applying to this service.</label>
        </div>
    </div>

    <div class="d-flex justify-content-center">
        <button class="button min-width-50">Upload item</button>
    </div>
</form>
