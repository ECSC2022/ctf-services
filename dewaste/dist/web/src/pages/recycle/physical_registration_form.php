<?php

use App\Model\PhysicalItem;
use App\Model\User;

/** @var PhysicalItem|null $item */
$item = $item ?? null;
/** @var bool|null $loggedIn */
$loggedIn = $loggedIn ?? false;
/** @var string|null $userType */
$userType = $userType ?? "account";
/** @var User|null $user */
$user = $user ?? null;
/** @var string|null $message */
$message = $message ?? "";
/** @var string|null $loginEmail */
$loginEmail = $loginEmail ?? "";

$_ = fn(string $unsafe) => htmlspecialchars($unsafe, ENT_QUOTES);
$checkedIf = fn(bool $checked) => $checked ? "checked" : "";
$itemVal = fn(string $name) => $_($item?->$name ?? "");
$userVal = fn(string $name) => $_($user?->$name ?? "");
?>

<h3>E-waste registration</h3>
<?= $message ?>
<form class="recycle-form" method="post">
    <fieldset>
        <h4>Basic information</h4>
        <div class="form-group">
            <label for="serial" class="form-label">Serial number</label>
            <input class="form-control" type="text" id="serial" name="serial" value="<?= $itemVal("serial") ?>"/>
        </div>
        <div class="form-group">
            <label for="item_description" class="form-label">Item description / Good to know</label>
            <textarea class="form-control" id="item_description" name="item_description"
            ><?= $itemVal("description") ?></textarea>
        </div>
    </fieldset>
    <fieldset>
        <h4>Dimensions and Weight</h4>

        <div class="d-flex align-items-center">
            <p>
                The dimensions of your item are required to allocate enough storage space in our 
                warehouse until items are processed. We only need <strong>rough numbers</strong>: 
                please take a measuring tape and round up to the <strong>next</strong> centimeter.
                We also need to know the weight of your item to prepare in advance the equipment 
                required to carry out the transport to the warehouse. If your items cannot be placed
                on racks, please send us a message via IPoAC beforehand. Notice that only solid
                items are accepted: recycling biological computers is an open challenge we are
                actively researching.
                <!-- although we heard that they taste great after being grilled -->
            </p>
            
        </div>

        <div class="row mb-2">
            <div class="col">
                <label for="length" class="form-label">Length<span class="unit">(in cm)</span></label>
                <input type="number" id="length" name="length" value="<?= $itemVal("length") ?>" min="0"
                       class="form-control" required placeholder="Length (in cm)"/>
            </div>
            <div class="col">
                <label for="width" class="form-label">Width<span class="unit">(in cm)</span></label>
                <input type="number" id="width" name="width" value="<?= $itemVal("width") ?>" min="0"
                       class="form-control" required placeholder="Width (in cm)"/>
            </div>
            <div class="col">
                <label for="height" class="form-label">Height<span class="unit">(in cm)</span></label>
                <input type="number" id="height" name="height" value="<?= $itemVal("height") ?>" min="0"
                       class="form-control" required placeholder="Height (in cm)"/>
            </div>
            <div class="col">
                <label for="weight" class="form-label">Weight<span class="unit">(in kg)</span></label>
                <input type="number" id="weight" name="weight" value="<?= $itemVal("weight") ?>" min="0" step="0.1"
                       class="form-control" required placeholder="Weight (in kg)"/>
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
        <button class="button min-width-50">Register item</button>
    </div>
</form>
