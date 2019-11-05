package com.mopub.unity;

import androidx.annotation.Nullable;

import com.mopub.mobileads.MoPubErrorCode;
import com.mopub.mobileads.MoPubInterstitial;


/**
 * Provides an API that bridges the Unity Plugin with the MoPub Interstitial SDK.
 */
public class MoPubInterstitialUnityPlugin extends MoPubUnityPlugin
        implements MoPubInterstitial.InterstitialAdListener {

    private MoPubInterstitial mMoPubInterstitial;

    /**
     * Creates a {@link MoPubInterstitialUnityPlugin} for the given ad unit ID.
     *
     * @param adUnitId String for the ad unit ID to use for this interstitial.
     */
    public MoPubInterstitialUnityPlugin(final String adUnitId) {
        super(adUnitId);
    }


    /* ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** *****
     * Interstitials API                                                                       *
     * ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** *****/

    /**
     * Loads an interstitial ad for the current ad unit ID and with the given keywords. Personally
     * Identifiable Information (PII) should ONLY be passed via
     * {@link #request(String, String)}
     *
     * @param keywords String with comma-separated key:value pairs of non-PII keywords.
     */
    public void request(final String keywords) {
        request(keywords, null);
    }
    /**
     * Loads an interstitial ad for the current ad unit ID and with the given keywords. Personally
     * Identifiable Information (PII) should ONLY be present in the userDataKeywords field.
     *
     * @param keywords String with comma-separated key:value pairs of non-PII keywords.
     * @param userDataKeywords String with comma-separated key:value pairs of PII keywords.
     */
    public void request(final String keywords, @Nullable final String userDataKeywords) {
        runSafelyOnUiThread(new Runnable() {
            public void run() {
                mMoPubInterstitial = new MoPubInterstitial(getActivity(), mAdUnitId);
                mMoPubInterstitial.setInterstitialAdListener(MoPubInterstitialUnityPlugin.this);

                mMoPubInterstitial.setKeywords(keywords);
                mMoPubInterstitial.setUserDataKeywords(userDataKeywords);
                mMoPubInterstitial.load();
            }
        });
    }

    /**
     * Check if the interstitial ad has finished loading.
     */
    public boolean isReady() {
        // TODO(ADF-4411): Replace this check with 3-layer validation in MoPub API.
        return mMoPubInterstitial != null && mMoPubInterstitial.isReady();
    }


    /**
     * Shows the loaded interstitial ad.
     */
    public void show() {
        runSafelyOnUiThread(new Runnable() {
            public void run() {
                mMoPubInterstitial.show();
            }
        });
    }


    /**
     * Destroy the interstitial ad.
     */
    public void destroy() {
        runSafelyOnUiThread(new Runnable() {
            @Override
            public void run() {
                mMoPubInterstitial.destroy();
            }
        });
    }


    /* ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** *****
     * InterstitialAdListener implementation                                                   *
     * ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** *****/

    @Override
    public void onInterstitialLoaded(MoPubInterstitial interstitial) {
        UnityEvent.InterstitialLoaded.Emit(mAdUnitId);
    }

    @Override
    public void onInterstitialFailed(MoPubInterstitial interstitial, MoPubErrorCode errorCode) {
        if (errorCode == MoPubErrorCode.EXPIRED)
            UnityEvent.InterstitialExpired.Emit(mAdUnitId);
        else
            UnityEvent.InterstitialFailed.Emit(mAdUnitId, errorCode.toString());
    }

    @Override
    public void onInterstitialShown(MoPubInterstitial interstitial) {
        UnityEvent.InterstitialShown.Emit(mAdUnitId);
    }

    @Override
    public void onInterstitialClicked(MoPubInterstitial interstitial) {
        UnityEvent.InterstitialClicked.Emit(mAdUnitId);
    }

    @Override
    public void onInterstitialDismissed(MoPubInterstitial interstitial) {
        UnityEvent.InterstitialDismissed.Emit(mAdUnitId);
    }
}
