import { useCallback } from "react";
import { useAuth0 } from "@auth0/auth0-react";
import * as surveysApi from "./surveys";
import type {
    CreateSurveyRequest,
    SurveyOut,
    SurveyVersionOut,
    UpdateSurveyRequest,
} from "./types";

export function useSurveysApi() {
    const { getAccessTokenSilently } = useAuth0();

    const getAuthHeaders = useCallback(async (): Promise<HeadersInit> => {
        const token = await getAccessTokenSilently({
            authorizationParams: {
                audience: import.meta.env.VITE_AUTH0_AUDIENCE,
            },
        });

        return {
            Authorization: `Bearer ${token}`,
        };
    }, [getAccessTokenSilently]);

    const listSurveys = useCallback(
        async (projectId: number): Promise<SurveyOut[]> => {
            const headers = await getAuthHeaders();
            return surveysApi.listSurveys(projectId, headers);
        },
        [getAuthHeaders],
    );

    const getSurvey = useCallback(
        async (projectId: number, surveyId: number): Promise<SurveyOut> => {
            const headers = await getAuthHeaders();
            return surveysApi.getSurvey(projectId, surveyId, headers);
        },
        [getAuthHeaders],
    );

    const createSurvey = useCallback(
        async (
            projectId: number,
            data: CreateSurveyRequest,
        ): Promise<SurveyOut> => {
            const headers = await getAuthHeaders();
            return surveysApi.createSurvey(projectId, data, headers);
        },
        [getAuthHeaders],
    );

    const updateSurvey = useCallback(
        async (
            projectId: number,
            surveyId: number,
            data: UpdateSurveyRequest,
        ): Promise<SurveyOut> => {
            const headers = await getAuthHeaders();
            return surveysApi.updateSurvey(projectId, surveyId, data, headers);
        },
        [getAuthHeaders],
    );

    const deleteSurvey = useCallback(
        async (projectId: number, surveyId: number): Promise<void> => {
            const headers = await getAuthHeaders();
            return surveysApi.deleteSurvey(projectId, surveyId, headers);
        },
        [getAuthHeaders],
    );

    const listVersions = useCallback(
        async (
            projectId: number,
            surveyId: number,
        ): Promise<SurveyVersionOut[]> => {
            const headers = await getAuthHeaders();
            return surveysApi.listVersions(projectId, surveyId, headers);
        },
        [getAuthHeaders],
    );

    const getVersion = useCallback(
        async (
            projectId: number,
            surveyId: number,
            versionId: number,
        ): Promise<SurveyVersionOut> => {
            const headers = await getAuthHeaders();
            return surveysApi.getVersion(projectId, surveyId, versionId, headers);
        },
        [getAuthHeaders],
    );

    const createVersion = useCallback(
        async (
            projectId: number,
            surveyId: number,
        ): Promise<SurveyVersionOut> => {
            const headers = await getAuthHeaders();
            return surveysApi.createVersion(projectId, surveyId, headers);
        },
        [getAuthHeaders],
    );

    const publishVersion = useCallback(
        async (
            projectId: number,
            surveyId: number,
            versionId: number,
        ): Promise<SurveyVersionOut> => {
            const headers = await getAuthHeaders();
            return surveysApi.publishVersion(projectId, surveyId, versionId, headers);
        },
        [getAuthHeaders],
    );

    const archiveVersion = useCallback(
        async (
            projectId: number,
            surveyId: number,
            versionId: number,
        ): Promise<SurveyVersionOut> => {
            const headers = await getAuthHeaders();
            return surveysApi.archiveVersion(projectId, surveyId, versionId, headers);
        },
        [getAuthHeaders],
    );

    return {
        listSurveys,
        getSurvey,
        createSurvey,
        updateSurvey,
        deleteSurvey,
        listVersions,
        getVersion,
        createVersion,
        publishVersion,
        archiveVersion,
    };
}